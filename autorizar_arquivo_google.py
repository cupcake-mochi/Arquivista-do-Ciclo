"""Mantenedor: libera um arquivo específico no drive.file, sem mudar credenciais ou editores.

Usa o Picker oficial para computador com PKCE; não executar na hospedagem.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from arquivista.config import load_env
from arquivista.existing_sheet import spreadsheet_id
from arquivista.domain import UserError
from configurar_google import authorize


def request_json(url, token=None, data=None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
        return json.load(response)


def refresh(values):
    body = urlencode({"client_id": values["GOOGLE_CLIENT_ID"], "client_secret": values["GOOGLE_CLIENT_SECRET"],
        "refresh_token": values["GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    return request_json("https://oauth2.googleapis.com/token", data=body)["access_token"]


def account(token):
    value = request_json("https://www.googleapis.com/drive/v3/about?fields=user(permissionId)", token)
    uid = value.get("user", {}).get("permissionId")
    if not uid:
        raise ValueError("Não foi possível confirmar a conta Google dedicada.")
    return uid


def authorize_existing(values, url):
    file_id = spreadsheet_id(url)
    owner = account(refresh(values))
    # O retorno novo é temporário, não substitui o refresh token em uso pelo bot.
    selected = authorize({"client_id": values["GOOGLE_CLIENT_ID"], "client_secret": values["GOOGLE_CLIENT_SECRET"]}, file_id=file_id)
    if account(selected) != owner:
        raise ValueError("Foi escolhida outra conta Google. Use a conta dedicada do Arquivista; as credenciais locais foram preservadas.")
    meta = request_json("https://www.googleapis.com/drive/v3/files/" + file_id + "?fields=id,isAppAuthorized,mimeType", refresh(values))
    if meta.get("id") != file_id or meta.get("isAppAuthorized") is not True or meta.get("mimeType") != "application/vnd.google-apps.spreadsheet":
        raise ValueError("O Google ainda não confirmou o acesso do aplicativo a essa planilha.")


def main():
    parser = argparse.ArgumentParser(description="Autoriza uma planilha específica para importação, sem ampliar o escopo do bot.")
    parser.add_argument("link", help="Link da planilha que será selecionada no Google Picker")
    args = parser.parse_args()
    load_env(Path(__file__).resolve().parent / ".env.google")
    values = {key: os.getenv(key, "").strip() for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")}
    if not all(values.values()):
        raise ValueError("Configure a conta dedicada primeiro. Consulte docs/GOOGLE-MANTENEDOR.md.")
    authorize_existing(values, args.link)
    print("Arquivo autorizado para o aplicativo. Nenhum editor foi adicionado e nenhuma credencial local foi alterada.")
    print("Agora use /planilha importar no Discord. A autorização da origem e a prévia ainda serão conferidas.")


if __name__ == "__main__":
    try:
        main()
    except HTTPError as exc:
        raise SystemExit(f"O Google recusou o pedido (HTTP {exc.code}). Confira o acesso ao arquivo e a ativação do Google Picker API.") from None
    except (ValueError, UserError) as exc:
        raise SystemExit(str(exc)) from None
    except (KeyError, OSError, URLError, KeyboardInterrupt):
        raise SystemExit("Autorização não concluída. Credenciais locais preservadas; consulte docs/GOOGLE-MANTENEDOR.md.") from None
