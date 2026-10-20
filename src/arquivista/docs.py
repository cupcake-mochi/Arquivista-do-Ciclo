"""Links públicos da documentação para quem usa e configura o bot."""

OWNER_GUIDE = "https://docs.google.com/document/d/1xuehlkhU3EhMsSE4hjLIfQY9p-eEF6ynS5ikAmlqnhw/view"
PRIVACY = "https://docs.google.com/document/d/1nMsutdyyrtb-YKCKziW3SmDY3ViKN31yO1OOW3zSRcw/view"
TERMS = "https://docs.google.com/document/d/1uZlohyKEn7eOlM1wP5TbSeDBm_PkpLc13YnGmPYpZx8/view"
SHEET_CODE = "https://drive.google.com/file/d/1-2UMIJg4TKzjXS5mFsy16221SVtZEncA/view"

DATA_LINKS = f"[Privacidade]({PRIVACY}) · [Termos de uso]({TERMS})"
SETUP_LINK = f"[Guia do dono do servidor]({OWNER_GUIDE})"
SCRIPT_UPDATE = (
    f"O script da planilha é antigo. Abra o [código da planilha]({SHEET_CODE}), "
    "copie o conteúdo inteiro e substitua o código no Apps Script. "
    "Depois use Implantar > Gerenciar implantações > Editar > Nova versão > Implantar. "
    f"O passo a passo está no {SETUP_LINK}."
)
