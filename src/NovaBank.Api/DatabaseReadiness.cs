using System.ComponentModel.DataAnnotations;
using Azure.Core;
using Npgsql;

namespace NovaBank.Api;

public sealed class DatabaseOptions
{
    [Required]
    public string Host { get; init; } = "";

    [Required]
    public string Name { get; init; } = "";

    [Required]
    public string Username { get; init; } = "";
}

public static class DatabaseConnection
{
    public static NpgsqlDataSource Create(DatabaseOptions options, TokenCredential credential)
    {
        Validator.ValidateObject(options, new ValidationContext(options), validateAllProperties: true);
        var connection = new NpgsqlConnectionStringBuilder
        {
            Host = options.Host,
            Database = options.Name,
            Username = options.Username,
            SslMode = SslMode.VerifyFull,
            Timeout = 5,
            CommandTimeout = 5,
            MaxPoolSize = 5,
            IncludeErrorDetail = false,
            LogParameters = false
        };
        var dataSource = new NpgsqlDataSourceBuilder(connection.ConnectionString);
        dataSource.UsePeriodicPasswordProvider(async (_, cancellationToken) =>
        {
            var token = await credential.GetTokenAsync(
                new TokenRequestContext(["https://ossrdbms-aad.database.windows.net/.default"]),
                cancellationToken);
            return token.Token;
        }, TimeSpan.FromMinutes(5), TimeSpan.FromSeconds(10));
        return dataSource.Build();
    }
}

public interface IDatabaseReadiness
{
    Task<bool> CheckAsync(CancellationToken cancellationToken);
}

public sealed class DatabaseReadiness(NpgsqlDataSource dataSource) : IDatabaseReadiness
{
    public async Task<bool> CheckAsync(CancellationToken cancellationToken)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(10));
        try
        {
            await using var command = dataSource.CreateCommand("SELECT 1");
            return await command.ExecuteScalarAsync(timeout.Token) is 1;
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new TimeoutException("Database readiness exceeded its time limit.");
        }
    }
}
