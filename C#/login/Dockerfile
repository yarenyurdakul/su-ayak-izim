FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /App
COPY *.csproj ./
RUN dotnet restore
COPY . ./
RUN dotnet publish -o out

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /App
COPY --from=build /App/out .
ENTRYPOINT ["dotnet", "login.dll"]