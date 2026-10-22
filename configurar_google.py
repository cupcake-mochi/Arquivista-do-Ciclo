"""Autorização única da conta Google do mantenedor. Não executar no Discord nem na hospedagem."""
from __future__ import annotations
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
import webbrowser
from configurar import write_private

SCOPE = "https://www.googleapis.com/auth/drive.file"

def authorization_url(client_id, redirect, state, verifier, file_id=None):
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    params = {
        "client_id": client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "state": state, "access_type": "offline", "prompt": "consent", "code_challenge": challenge,
        "code_challenge_method": "S256"}
    if file_id:
        params.update(trigger_onepick="true", allow_multiple="false", file_ids=file_id,
                      mimetypes="application/vnd.google-apps.spreadsheet")
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)

def authorize(client, *, file_id=None):
    result, state, verifier = {}, secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # a URL contém o código de autorização; nunca vai para o console
        def do_GET(self):
            query = parse_qs(urlsplit(self.path).query)
            valid = urlsplit(self.path).path == "/callback" and secrets.compare_digest(query.get("state", [""])[0], state)
            code = query.get("code", [""])[0]
            self.send_response(200 if valid else 400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            if valid:
                result.update(code=code, denied=bool(query.get("error")), picked=query.get("picked_file_ids", [""])[0])
                self.wfile.write("Autorização recebida. Volte ao terminal; esta aba pode ser fechada.".encode())
            else:
                self.wfile.write(b"Pedido invalido.")
    with HTTPServer(("127.0.0.1", 0), Callback) as server:
        server.timeout = 1
        redirect = f"http://127.0.0.1:{server.server_port}/callback"
        url = authorization_url(client["client_id"], redirect, state, verifier, file_id)
        print("Abra o link na conta Google dedicada ao Arquivista e conclua a autorização:")
        print(url)  # somente client_id público, state aleatório e desafio PKCE; nenhum segredo
        webbrowser.open(url)
        deadline = time.monotonic() + 300
        while not result and time.monotonic() < deadline:
            server.handle_request()
    if not result.get("code") or result.get("denied"):
        raise ValueError("A autorização não foi concluída em cinco minutos. Execute novamente quando estiver pronto.")
    if file_id and result.get("picked") != file_id:
        raise ValueError("Selecione somente a planilha indicada. Nenhuma configuração local foi alterada.")
    body = urlencode({"client_id": client["client_id"], "client_secret": client["client_secret"],
        "code": result["code"], "code_verifier": verifier, "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    req = Request("https://oauth2.googleapis.com/token", data=body)
    with urlopen(req, timeout=30) as response:
        data = json.load(response)
    if file_id:
        if not data.get("access_token") or (data.get("scope") and set(data["scope"].split()) != {SCOPE}):
            raise ValueError("O Google não confirmou o acesso restrito ao arquivo.")
        return data["access_token"]
    if not data.get("refresh_token"):
        raise ValueError("O Google não retornou autorização permanente. Confira o consentimento e tente novamente.")
    return {"GOOGLE_CLIENT_ID": client["client_id"], "GOOGLE_CLIENT_SECRET": client["client_secret"],
            "GOOGLE_REFRESH_TOKEN": data["refresh_token"]}

def main():
    parser = argparse.ArgumentParser(description="Conecta a conta Google do Arquivista uma única vez.")
    parser.add_argument("cliente", type=Path, help="JSON de um cliente OAuth do tipo Aplicativo para computador")
    args = parser.parse_args()
    client = json.loads(args.cliente.read_text(encoding="utf-8-sig")).get("installed")
    if not client or not client.get("client_id") or not client.get("client_secret"):
        raise ValueError("Use o JSON de um cliente OAuth do tipo Aplicativo para computador; não use conta de serviço.")
    path = Path(__file__).resolve().parent / ".env.google"
    if path.exists():
        raise ValueError(".env.google já existe. Guarde esse arquivo em local privado e renomeie-o antes de autorizar novamente.")
    values = authorize(client)
    write_private(path, values)
    print("Autorização salva em .env.google. Nenhum token foi impresso.")
    print("Na sua máquina, o bot lê esse arquivo. Na Discloud, cadastre as três variáveis no painel e faça rebuild ou deploy para aplicá-las.")
    print("Não publique o JSON do cliente nem o .env.google.")

if __name__ == "__main__":
    try:
        main()
    except HTTPError as exc:
        raise SystemExit(f"O Google recusou a autorização (HTTP {exc.code}). Confira a configuração OAuth.") from None
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    except (KeyError, OSError, URLError, KeyboardInterrupt):
        raise SystemExit("Autorização não concluída. Confira o arquivo do cliente OAuth, a rede e as instruções em docs/GOOGLE-MANTENEDOR.md.") from None
