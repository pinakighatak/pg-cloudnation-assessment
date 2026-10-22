using System.ComponentModel.DataAnnotations;
using Azure.Identity;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using NovaBank.Api;
using Npgsql;
using Xunit;

namespace NovaBank.Api.Tests;

public sealed class HealthFunctionsTests
{
    private static HealthFunctions Create(Func<CancellationToken, Task<bool>> check)
        => new(new Probe(check), NullLogger<HealthFunctions>.Instance);

    [Fact]
    public void HealthDoesNotQueryDatabase()
    {
        var functions = Create(_ => throw new InvalidOperationException("Must not query database."));
        var response = Assert.IsType<OkObjectResult>(functions.Health(new DefaultHttpContext().Request));
        Assert.Equal(new HealthResponse("healthy"), response.Value);
    }

    [Fact]
    public async Task ReadinessReturnsReadyAfterSuccessfulQuery()
    {
        var response = await Create(_ => Task.FromResult(true))
            .Readiness(new DefaultHttpContext().Request, CancellationToken.None);
        Assert.Equal(new HealthResponse("ready"), Assert.IsType<OkObjectResult>(response).Value);
    }

    [Fact]
    public async Task UnexpectedQueryResultIsNotReady()
    {
        var response = await Create(_ => Task.FromResult(false))
            .Readiness(new DefaultHttpContext().Request, CancellationToken.None);
        Assert.Equal(503, Assert.IsType<ObjectResult>(response).StatusCode);
    }

    [Theory]
    [InlineData("postgres")]
    [InlineData("timeout")]
    [InlineData("identity")]
    public async Task DependencyFailureIs503WithoutLeakingDetails(string failure)
    {
        Exception exception = failure switch
        {
            "postgres" => new NpgsqlException("sensitive database detail"),
            "timeout" => new TimeoutException("sensitive timeout detail"),
            _ => new AuthenticationFailedException("sensitive identity detail")
        };
        var response = await Create(_ => Task.FromException<bool>(exception))
            .Readiness(new DefaultHttpContext().Request, CancellationToken.None);
        var result = Assert.IsType<ObjectResult>(response);
        Assert.Equal(503, result.StatusCode);
        Assert.Equal(new HealthResponse("not-ready"), result.Value);
    }

    [Fact]
    public async Task CancellationPropagates()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            Create(token => Task.FromCanceled<bool>(token))
                .Readiness(new DefaultHttpContext().Request, cancellation.Token));
    }

    [Fact]
    public void MissingDatabaseSettingsFailExplicitly()
        => Assert.Throws<ValidationException>(() =>
            DatabaseConnection.Create(new DatabaseOptions(), new DefaultAzureCredential()));

    private sealed class Probe(Func<CancellationToken, Task<bool>> check) : IDatabaseReadiness
    {
        public Task<bool> CheckAsync(CancellationToken cancellationToken) => check(cancellationToken);
    }
}
