using Azure.Identity;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;
using Npgsql;

namespace NovaBank.Api;

public sealed record HealthResponse(string Status);

public sealed class HealthFunctions(IDatabaseReadiness database, ILogger<HealthFunctions> logger)
{
    // Function keys are intentionally unused: App Service Authentication enforces Entra access.
    [Function("Health")]
    public IActionResult Health(
        [HttpTrigger(AuthorizationLevel.Anonymous, "get", Route = "health")] HttpRequest request)
        => new OkObjectResult(new HealthResponse("healthy"));

    [Function("Readiness")]
    public async Task<IActionResult> Readiness(
        [HttpTrigger(AuthorizationLevel.Anonymous, "get", Route = "ready")] HttpRequest request,
        CancellationToken cancellationToken)
    {
        try
        {
            if (await database.CheckAsync(cancellationToken))
            {
                return new OkObjectResult(new HealthResponse("ready"));
            }

            logger.LogWarning("Database readiness returned an unexpected result");
        }
        catch (Exception exception) when (
            exception is NpgsqlException or TimeoutException or AuthenticationFailedException)
        {
            logger.LogWarning("Database readiness failed: {FailureType}", exception.GetType().Name);
        }

        return new ObjectResult(new HealthResponse("not-ready"))
        {
            StatusCode = StatusCodes.Status503ServiceUnavailable
        };
    }
}
