using System;
using System.Text;
using System.Collections.Generic;
using System.Security.Claims;
using System.IdentityModel.Tokens.Jwt;
using Microsoft.IdentityModel.Tokens;
using MySql.Data.MySqlClient;
using BCrypt.Net;
using Scalar.AspNetCore; 
using System.Text.Json.Serialization;



var builder = WebApplication.CreateBuilder(args); 
builder.WebHost.UseUrls("http://0.0.0.0:8080");   

// --- 1. SERVİS KAYITLARI (BUILDER) ---

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");

builder.Services.AddOpenApi(); 

builder.Services.AddCors(options => 
    options.AddDefaultPolicy(p => p.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader()));

// JWT Ayarları
var jwtSecretKey = builder.Configuration["JwtSettings:SecretKey"];
if (string.IsNullOrEmpty(jwtSecretKey)) {
    throw new Exception("JWT SecretKey appsettings.json içinde bulunamadı!");
}
var key = Encoding.ASCII.GetBytes(jwtSecretKey);

builder.Services.AddAuthentication(options => {
    options.DefaultAuthenticateScheme = "Bearer";
    options.DefaultChallengeScheme = "Bearer";
}).AddJwtBearer(options => {
    options.TokenValidationParameters = new TokenValidationParameters {
        ValidateIssuerSigningKey = true,
        IssuerSigningKey = new SymmetricSecurityKey(key),
        ValidateIssuer = false,
        ValidateAudience = false
    };
});

builder.Services.AddAuthorization();

// --- APP KISMI ---

var app = builder.Build();


if (app.Environment.IsDevelopment())
{
    app.MapOpenApi(); 
    app.MapScalarApiReference(); 
}

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();

// --- 3. ENDPOINT'LER ---

app.MapPost("/kayit-ol", async (UserInformation veri) => {
    long yeniKullaniciId = 0;
    await using (var connection = new MySqlConnection(connectionString))
    {
        await connection.OpenAsync();

        // Mail kontrolü
        string checksql = "SELECT COUNT(*) FROM Users WHERE mail = @mail"; 
        var checkcmd = new MySqlCommand(checksql, connection);
        checkcmd.Parameters.AddWithValue("@mail", veri.Mail);

        var result = await checkcmd.ExecuteScalarAsync();
        if (Convert.ToInt64(result) > 0)
        {
            return Results.BadRequest("Bu mail kayıtlı lüften başka bir mail deneyiniz.");
        }

        string checkUserSql = "SELECT COUNT(*) FROM Users WHERE nickname = @nick"; 
        var checkUserCmd = new MySqlCommand(checkUserSql, connection);
        checkUserCmd.Parameters.AddWithValue("@nick", veri.Nickname);

        var nickResult = await checkUserCmd.ExecuteScalarAsync();
        if(Convert.ToInt64(nickResult)>0)
        {
            return Results.BadRequest("Bu isim başka biri tarafından kullanılıyor lütfen başka bir isim giriniz.");
        }

        // Şifreleme ve Kayıt
        string hashedPassword = BCrypt.Net.BCrypt.HashPassword(veri.Password);
        string insertsql = "INSERT INTO Users (nickname, mail, password) VALUES (@nick, @mail, @pass)"; 
        var insertcmd = new MySqlCommand(insertsql, connection);
        insertcmd.Parameters.AddWithValue("@nick", veri.Nickname);
        insertcmd.Parameters.AddWithValue("@mail", veri.Mail);
        insertcmd.Parameters.AddWithValue("@pass", hashedPassword);

        await insertcmd.ExecuteNonQueryAsync();

        yeniKullaniciId = insertcmd.LastInsertedId;

   
        string cicekSql = "INSERT INTO cicek_durumu (kullanici_id, son_sulanma_tarihi) VALUES (@user_id, @bugun)";
        var cicekCmd = new MySqlCommand(cicekSql, connection);
        cicekCmd.Parameters.AddWithValue("@user_id", yeniKullaniciId);
        cicekCmd.Parameters.AddWithValue("@bugun", DateTime.Now.Date); 
        
        await cicekCmd.ExecuteNonQueryAsync();
    }
    return Results.Ok(new { Message = $"Kayıt Başarılı. Hoşgeldin {veri.Nickname}",user_id = yeniKullaniciId });
});

app.MapPost("/giris-yap", async (UserInformation veri) => {
    await using (var connection = new MySqlConnection(connectionString))
    {
        await connection.OpenAsync();
        
        bool isVerified = false;
        int authenticatedUserId = 0;
        string authenticatedNick = "";

        string checkLoginSql = "SELECT ID, nickname, password FROM Users WHERE mail = @mail";
        var loginCmd = new MySqlCommand(checkLoginSql, connection);
        loginCmd.Parameters.AddWithValue("@mail", veri.Mail);
        
        using (var reader = await loginCmd.ExecuteReaderAsync())
        {
            if (await reader.ReadAsync())
            {
                string storedHash = reader.GetString(2);
                if (BCrypt.Net.BCrypt.Verify(veri.Password, storedHash))
                {
                    isVerified = true;
                    authenticatedUserId = reader.GetInt32(0);
                    authenticatedNick = reader.GetString(1);
                }
            }
        } 

        if (isVerified)
        {
            bool anketCozulduMu = false;
            string anketSql = "SELECT COUNT(*) FROM answers WHERE kullanici_id = @user_id";
            var anketCmd = new MySqlCommand(anketSql, connection);
            anketCmd.Parameters.AddWithValue("@user_id", authenticatedUserId);
            
            var anketResult = await anketCmd.ExecuteScalarAsync();
            if (Convert.ToInt64(anketResult) > 0)
            {
                anketCozulduMu = true; 
            }

            // JWT Üretme
            var tokenHandler = new JwtSecurityTokenHandler();
            var tokenDescriptor = new SecurityTokenDescriptor {
                Subject = new ClaimsIdentity(new[] { 
                    new Claim("nickname", authenticatedNick),
                    new Claim("email", veri.Mail),
                    new Claim(ClaimTypes.NameIdentifier, authenticatedUserId.ToString())
                }),
                Expires = DateTime.UtcNow.AddYears(1), 
                SigningCredentials = new SigningCredentials(
                    new SymmetricSecurityKey(key), 
                    SecurityAlgorithms.HmacSha256Signature)
            };
            
            var token = tokenHandler.CreateToken(tokenDescriptor);
            
            return Results.Ok(new { 
                Message = $"Hoşgeldin {authenticatedNick}", 
                Token = tokenHandler.WriteToken(token),
                user_id = authenticatedUserId,
                sorular_cozuldu_mu = anketCozulduMu 
            });
        }
    }  
    return Results.Unauthorized();
});

app.MapPost("/profil-guncelle", async (UpdateProfileRequest veri) => {
    

    if (string.IsNullOrWhiteSpace(veri.NewNickname)) {
        return Results.BadRequest(new { Message = "İsim alanı boş bırakılamaz veya eşleşmedi!" });
    }

    await using (var connection = new MySqlConnection(connectionString))
    {
        await connection.OpenAsync();

        string sql = "UPDATE Users SET nickname = @nick WHERE ID = @id";
        var cmd = new MySqlCommand(sql, connection);
        cmd.Parameters.AddWithValue("@nick", veri.NewNickname);
        cmd.Parameters.AddWithValue("@id", veri.UserId);

        int rowsAffected = await cmd.ExecuteNonQueryAsync();

        if (rowsAffected > 0)
        {
  
            return Results.Ok(new { 
                Message = "Profil başarıyla güncellendi.",
                guncel_isim = veri.NewNickname 
            });
        }
    }
    return Results.BadRequest(new { Message = "Güncelleme yapılamadı." });
}).RequireAuthorization();



app.MapPost("/sifre-degistir", async (ChangePasswordRequest veri, HttpContext httpContext) => {
    
    
    var userIdString = httpContext.User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
    

    if (string.IsNullOrEmpty(userIdString)) 
    {
        return Results.Unauthorized(); 
    }

    int userId = int.Parse(userIdString); 

    await using (var connection = new MySqlConnection(connectionString))
    {
        await connection.OpenAsync();


        string getSql = "SELECT password FROM Users WHERE ID = @id";
        var getCmd = new MySqlCommand(getSql, connection);
        getCmd.Parameters.AddWithValue("@id", userId); 

        string? storedHash = await getCmd.ExecuteScalarAsync() as string;

        if (string.IsNullOrEmpty(storedHash)) return Results.NotFound("Kullanıcı bulunamadı.");

        // 3. Eski şifreyi doğruluyoruz
        if (!BCrypt.Net.BCrypt.Verify(veri.CurrentPassword, storedHash))
        {
            return Results.BadRequest("Mevcut şifreniz hatalı.");
        }

        // 4. Yeni şifreyi hashleyip kaydediyoruz
        string newHashedPassword = BCrypt.Net.BCrypt.HashPassword(veri.NewPassword);
        string updateSql = "UPDATE Users SET password = @pass WHERE ID = @id";
        var updateCmd = new MySqlCommand(updateSql, connection);
        updateCmd.Parameters.AddWithValue("@pass", newHashedPassword);
        updateCmd.Parameters.AddWithValue("@id", userId);

        await updateCmd.ExecuteNonQueryAsync();
    }
    
    return Results.Ok(new { Message = "Şifreniz başarıyla değiştirildi." });
}).RequireAuthorization();

app.MapPost("/hesabimi-sil", async (DeleteAccountRequest veri) => {
    await using (var connection = new MySqlConnection(connectionString))
    {
        await connection.OpenAsync();
        

        using var transaction = await connection.BeginTransactionAsync();

        try
        {

            string[] tablolar = { "answers", "cicek_durumu", "kullanici_su_durumu", "su_gecmisi", "calculate" };

            foreach(var tablo in tablolar)
            {
                string sql = $"DELETE FROM {tablo} WHERE kullanici_id = @id";
                var cmd = new MySqlCommand(sql, connection, transaction);
                cmd.Parameters.AddWithValue("@id", veri.UserId);
                await cmd.ExecuteNonQueryAsync();
            }

            string deleteUserSql = "DELETE FROM Users WHERE ID = @id";
            var userCmd = new MySqlCommand(deleteUserSql, connection, transaction);
            userCmd.Parameters.AddWithValue("@id", veri.UserId);
            int rowsAffected = await userCmd.ExecuteNonQueryAsync();

            if (rowsAffected > 0) 
            {
                await transaction.CommitAsync();
                return Results.Ok(new { Message = "Hesabınız ve tüm verileriniz kalıcı olarak silindi." });
            } 
            else 
            {

                await transaction.RollbackAsync();
                return Results.NotFound("Kullanıcı bulunamadı.");
            }
        }
        catch (Exception ex)
        {
            await transaction.RollbackAsync();
            return Results.BadRequest(new { Message = "Silme işlemi sırasında bir hata oluştu.", Detail = ex.Message });
        }
    }
}).RequireAuthorization();

app.Run();

// --- 4. MODELLER ---

class UserInformation { 
    public string? Nickname { get; set; } 
    public string Mail { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
}

class UpdateProfileRequest {
    [JsonPropertyName("user_id")]
    public int UserId { get; set; }
    
    [JsonPropertyName("ad_soyad")] 
    public string NewNickname { get; set; } = string.Empty;
}

class ChangePasswordRequest {
    [JsonPropertyName("user_id")]
    public int UserId { get; set; }
    
    public string CurrentPassword { get; set; } = string.Empty;
    public string NewPassword { get; set; } = string.Empty;
}

class DeleteAccountRequest {
    [JsonPropertyName("user_id")]
    public int UserId { get; set; }
}

 