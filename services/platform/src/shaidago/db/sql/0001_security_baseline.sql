-- Security baseline (ADR-0003): roles, schemas, and default privileges.
-- Idempotent and versioned: a corrective change is a new numbered file, never an edit.
-- Roles are created NOLOGIN. Passwords and LOGIN are granted by the deployment step
-- (`shaidago.db.roles.enable_login`), so no credential lives in source control.

DO $$
DECLARE
    role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY[
        'shaidago_owner', 'shaidago_public', 'shaidago_reviewer',
        'shaidago_worker', 'shaidago_readonly_ops'
    ] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format(
                'CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
                role_name
            );
        END IF;
    END LOOP;
END
$$;

-- The migrating user acts as the owner so every object is owned by shaidago_owner.
GRANT shaidago_owner TO CURRENT_USER WITH SET TRUE;

-- Nothing is reachable by default: PUBLIC loses database connect and the public schema.
DO $$
BEGIN
    EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
    EXECUTE format(
        'GRANT CONNECT ON DATABASE %I TO shaidago_owner, shaidago_public, shaidago_reviewer, '
        'shaidago_worker, shaidago_readonly_ops',
        current_database()
    );
END
$$;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- "app" holds tables (private by default); "public_api" holds views over public columns only.
CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION shaidago_owner;
CREATE SCHEMA IF NOT EXISTS public_api AUTHORIZATION shaidago_owner;
REVOKE ALL ON SCHEMA app, public_api FROM PUBLIC;

-- USAGE lets a role resolve names; it grants no table access. Every table migration grants
-- its own privileges and policies in the same revision.
GRANT USAGE ON SCHEMA app TO
    shaidago_public, shaidago_reviewer, shaidago_worker, shaidago_readonly_ops;
GRANT USAGE ON SCHEMA public_api TO
    shaidago_public, shaidago_reviewer, shaidago_worker, shaidago_readonly_ops;

-- Tables in "app" are born with no grants for anyone but the owner.
ALTER DEFAULT PRIVILEGES FOR ROLE shaidago_owner IN SCHEMA app
    REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE shaidago_owner IN SCHEMA app
    REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE shaidago_owner IN SCHEMA app
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
-- Views in "public_api" are readable by the application roles; a view may project public
-- columns only, and reviewers of every migration check that.
ALTER DEFAULT PRIVILEGES FOR ROLE shaidago_owner IN SCHEMA public_api
    GRANT SELECT ON TABLES TO shaidago_public, shaidago_reviewer, shaidago_worker;
