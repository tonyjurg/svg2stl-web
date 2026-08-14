# DSM User Authentication

This application does not contain user accounts or a login page. DSM can still
provide the user identity by running **SSO Server** as an OpenID Connect (OIDC)
provider. An authentication proxy is required between DSM's reverse proxy and
the SVG-to-STL application because the application itself is not an OIDC
client.

## What DSM does and does not provide

DSM's built-in reverse proxy provides HTTPS routing and source-IP access
control. A reverse-proxy rule or Container Manager Web Station portal does not,
by itself, require users to sign in with a DSM account. Synology describes its
reverse-proxy access-control profiles as IP/CIDR rules.

For actual user authentication, use this flow:

![Authentication flow: the user reaches the DSM reverse proxy over HTTPS,
which forwards to OAuth2 Proxy. OAuth2 Proxy signs in through DSM SSO Server
and forwards authenticated requests to SVG to STL Web.](assets/authentication-flow.svg)

This guide uses
[OAuth2 Proxy](https://oauth2-proxy.github.io/oauth2-proxy/) as the OIDC client.
DSM accounts and optional Synology Secure SignIn methods remain managed by
Synology SSO Server.

## Prerequisites

- DSM 7.2 or newer with **SSO Server** available in Package Center
- A domain name for the NAS, such as `nas.example.net`
- A valid TLS certificate assigned to that DSM hostname
- A second HTTPS name for the application, such as `stl.example.net`
- Local DNS records that resolve both names to the NAS on the home network
- Administrative access to DSM, Container Manager, certificates, and users

Synology requires the SSO Server URL to be an HTTPS domain with a valid TLS
certificate. It cannot be an IP address and cannot use QuickConnect. See
[SSO Server General Settings](https://kb.synology.com/en-ph/DSM/help/SSOServer/sso_server_general_setting?version=7)
and the
[SSO Server technical specifications](https://www.synology.com/en-global/dsm/7.4/software_spec/sso_server).

## 1. Prepare DSM accounts and HTTPS names

1. Create or review the DSM users who should be allowed to sign in.
2. Give every intended user a unique email address. OAuth2 Proxy normally uses
   the OIDC email claim when deciding who may access the application.
3. Enable two-factor authentication or Synology Secure SignIn where appropriate.
4. Add DNS records for the SSO hostname and application hostname.
5. Import or request valid certificates under **Control Panel > Security >
   Certificate** and assign them to the corresponding DSM services.

Do not proceed with a self-signed or mismatched certificate unless every client
and container has been configured to trust that certificate authority. Do not
disable OIDC TLS verification as a shortcut.

## 2. Configure Synology SSO Server

1. Install and open **SSO Server** from Package Center.
2. Under **General Settings**, select the account type that contains the users
   you want to authenticate. For ordinary DSM accounts, use the option that
   includes local users.
3. Set **Server URL** to the externally valid DSM SSO URL, for example
   `https://nas.example.net:5001`.
4. Under **Service**, enable **OIDC**.
5. Copy the displayed **Well-known URL** for later use.
6. Under **Application**, select **Add > OIDC**.
7. Use `SVG to STL Web` as the application name.
8. Add this exact redirect URI, substituting your real application hostname:

   ```text
   https://stl.example.net/oauth2/callback
   ```

9. Save the application, edit it again, and copy its **Application ID** and
   **Application secret**. These are the OAuth client ID and client secret.
10. If the application profile offers attribute mapping, include the user's
    email address as the standard OIDC `email` claim.

Synology's current OIDC application procedure is documented in
[SSO Server: Application](https://kb.synology.com/en-nz/PAS/help/SSOServer/sso_server_application_list).
The redirect URI must match exactly, including scheme, hostname, path, and any
non-standard port.

### Determine the issuer URL

OAuth2 Proxy needs the OIDC **issuer URL**, while DSM presents a **Well-known
URL**. Open the Well-known URL and read the JSON document. Use the exact value
of its `issuer` property as `OAUTH2_PROXY_OIDC_ISSUER_URL`.

Do not construct or guess the issuer path. It can differ between DSM versions
and SSO Server configurations.

## 3. Create the authentication secret file

In the project directory on the NAS, create `.env.auth`. This filename is
ignored by Git. Do not commit or paste its values into an issue.

Generate a random cookie secret on a computer with OpenSSL:

```bash
openssl rand -base64 32
```

Create `.env.auth` with the values from DSM:

```dotenv
OAUTH2_PROXY_PROVIDER=oidc
OAUTH2_PROXY_OIDC_ISSUER_URL=https://issuer-value-from-well-known-json
OAUTH2_PROXY_CLIENT_ID=application-id-from-dsm
OAUTH2_PROXY_CLIENT_SECRET=application-secret-from-dsm
OAUTH2_PROXY_COOKIE_SECRET=random-cookie-secret
OAUTH2_PROXY_REDIRECT_URL=https://stl.example.net/oauth2/callback
OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE=/etc/oauth2-proxy/allowed-emails.txt
OAUTH2_PROXY_SCOPE=openid profile email
OAUTH2_PROXY_COOKIE_SECURE=true
OAUTH2_PROXY_COOKIE_SAMESITE=lax
OAUTH2_PROXY_SKIP_PROVIDER_BUTTON=true
OAUTH2_PROXY_REVERSE_PROXY=true
OAUTH2_PROXY_HTTP_ADDRESS=0.0.0.0:4180
OAUTH2_PROXY_UPSTREAMS=http://svg2stl-web:8080/
```

Create `allowed-emails.txt` beside the Compose file and put one approved DSM
user email address on each line. This filename is also ignored by Git:

```text
alice@example.net
bob@example.net
```

DSM authenticates the account; this file authorizes the individual account for
this application. To allow every account accepted by SSO Server instead, remove
`OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE` and set
`OAUTH2_PROXY_EMAIL_DOMAINS=*`. Do not configure both and assume the file still
acts as a restrictive allowlist.

Treat the application secret and cookie secret like passwords. Give
`.env.auth` read permission only to the NAS administrator account used to
manage the Container Manager project. The allowlist is not a secret, but it
contains user identities and must be readable by OAuth2 Proxy's non-root
container user (`65532`). Keep its bind mount read-only and restrict access to
the surrounding project folder with DSM permissions.

## 4. Put OAuth2 Proxy in front of the application

Update the Compose project so the application is reachable only from other
containers and OAuth2 Proxy is bound only to the NAS loopback interface. The
important point is to remove the existing `8080:8080` publication.

The service portion should follow this pattern:

```yaml
services:
  svg2stl-web:
    build:
      context: .
    container_name: svg2stl-web
    restart: unless-stopped
    # No ports entry: direct access would bypass authentication.
    expose:
      - "8080"
    environment:
      MAX_UPLOAD_BYTES: "5242880"
      CONVERSION_TIMEOUT_SECONDS: "180"
      MAX_CONCURRENT_CONVERSIONS: "1"
      DIAGNOSTIC_ERRORS: "false"
    read_only: true
    tmpfs:
      - /tmp:size=256m,mode=1777
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    pids_limit: 128
    mem_limit: 1g

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.15.3
    container_name: svg2stl-auth
    restart: unless-stopped
    depends_on:
      - svg2stl-web
    env_file:
      - .env.auth
    volumes:
      - ./allowed-emails.txt:/etc/oauth2-proxy/allowed-emails.txt:ro
    ports:
      - "127.0.0.1:4180:4180"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
```

The version above is an intentional fixed release. Check the
[OAuth2 Proxy releases](https://github.com/oauth2-proxy/oauth2-proxy/releases)
for security updates before deploying, and test newer versions before changing
the pin.

Rebuild the project in Container Manager. The SVG-to-STL container should no
longer display a published host port. OAuth2 Proxy should publish only
`127.0.0.1:4180`.

## 5. Create the DSM reverse-proxy rule

Open **Control Panel > Login Portal > Advanced > Reverse Proxy**, then create a
rule with these values:

| Setting | Value |
| --- | --- |
| Source protocol | HTTPS |
| Source hostname | `stl.example.net` |
| Source port | `443` |
| Destination protocol | HTTP |
| Destination hostname | `127.0.0.1` |
| Destination port | `4180` |

Assign the certificate for `stl.example.net` to the rule. Increase the proxy
read timeout above the application's conversion timeout, for example to 240
seconds, so DSM does not terminate a valid long conversion first.

The DSM procedure and timeout settings are described in Synology's
[reverse-proxy guide](https://kb.synology.com/en-global/DSM/help/DSM/AdminCenter/system_login_portal_advanced?version=7).

Do not create a second DSM rule that routes around OAuth2 Proxy to port 8080.

## 6. Verify that authentication cannot be bypassed

Use a private browser window and perform all of these checks:

1. Open `https://stl.example.net`.
2. Confirm that the browser is redirected to the Synology SSO login page.
3. Sign in with an allowed non-administrator DSM account.
4. Confirm that the SVG-to-STL page appears and a conversion completes.
5. Sign out or clear the proxy cookie and confirm the login is required again.
6. Open `http://NAS-IP:8080` from another LAN device and confirm that it fails.
7. Try a DSM account that should not be allowed and confirm access is denied.
8. Review SSO Server and OAuth2 Proxy logs for the corresponding login events.

The sixth check is essential. A working SSO login does not provide protection
if the original application port remains reachable as an unauthenticated
alternative.

## API access after enabling authentication

The browser API at `/api/convert` is protected by the same login session.
Unauthenticated command-line `curl` calls will receive a redirect instead of an
STL. OAuth2 Proxy can support bearer-token and service-account patterns, but
those require a separate authorization design and are intentionally outside
this basic DSM-user setup.

Do not add an unauthenticated bypass for `/api/convert`. If monitoring needs an
unprotected health check, keep it inside the Docker network or NAS loopback
interface rather than exposing it publicly.

## Troubleshooting

### Redirect URI mismatch or login loop

- Compare DSM's registered redirect URI with
  `OAUTH2_PROXY_REDIRECT_URL` character for character.
- Confirm DSM sees the public scheme as HTTPS. Keep
  `OAUTH2_PROXY_REVERSE_PROXY=true`.
- Confirm the DSM reverse proxy sends the original host and forwarded protocol.
- Use the exact `issuer` value from the Well-known JSON.
- Check that both HTTPS names have valid certificates and resolve to the NAS.

### Login succeeds but OAuth2 Proxy rejects the account

Confirm that DSM returns an `email` claim and that the user's DSM profile has a
unique email address. Review any OIDC attribute mapping configured for the SSO
application. Avoid enabling OAuth2 Proxy's unverified-email compatibility flag
unless you understand and accept the weaker identity assurance.

### DSM login works but direct port 8080 still opens

The application still has a host `ports` mapping. Remove `8080:8080`, rebuild
the project, and check Container Manager again. `expose: 8080` is internal to
the Compose network; `ports: 8080:8080` publishes a bypass on the NAS.

### SSO Server refuses an IP address or QuickConnect URL

This is expected. Synology requires a proper HTTPS domain and explicitly does
not support QuickConnect as the SSO Server URL.
