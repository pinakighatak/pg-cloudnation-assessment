using Azure.Core;
using Azure.Identity;
using Microsoft.ApplicationInsights.Extensibility;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using NovaBank.Api;
using Npgsql;

var builder = FunctionsApplication.CreateBuilder(args);
builder.ConfigureFunctionsWebApplication();

TokenCredential credential = builder.Environment.IsDevelopment()
    ? new DefaultAzureCredential()
    : new ManagedIdentityCredential(ManagedIdentityId.FromUserAssignedClientId(
        builder.Configuration["AZURE_CLIENT_ID"]
        ?? throw new InvalidOperationException("AZURE_CLIENT_ID is required.")));

builder.Services.AddSingleton(credential);
builder.Services.AddApplicationInsightsTelemetryWorkerService();
builder.Services.ConfigureFunctionsApplicationInsights();
builder.Services.Configure<TelemetryConfiguration>(configuration =>
    configuration.SetAzureTokenCredential(credential));
builder.Services.AddOptions<DatabaseOptions>()
    .BindConfiguration("Database")
    .ValidateDataAnnotations()
    .ValidateOnStart();
builder.Services.AddSingleton<NpgsqlDataSource>(services =>
    DatabaseConnection.Create(
        services.GetRequiredService<IOptions<DatabaseOptions>>().Value,
        services.GetRequiredService<TokenCredential>()));
builder.Services.AddSingleton<IDatabaseReadiness, DatabaseReadiness>();

builder.Build().Run();
