SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role_name') AS role_exists \gset
\if :role_exists
    SELECT EXISTS (
        SELECT 1 FROM pgaadauth_list_principals(false) AS principal
        WHERE principal.rolename = :'role_name'
          AND EXISTS (
              SELECT 1 FROM jsonb_each_text(to_jsonb(principal)) AS field
              WHERE lower(field.key) = 'objectid' AND lower(field.value) = lower(:'principal_id')
          )
    ) AS principal_matches \gset
    \if :principal_matches
        \echo Existing principal matches the requested managed identity.
    \else
        \echo FAILED: existing database role does not match the managed identity object ID.
        \quit 1
    \endif
\else
    SELECT * FROM pgaadauth_create_principal_with_oid(
        :'role_name', :'principal_id', 'service', false, false
    );
\endif
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'database_name') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'database_name', :'role_name') \gexec
