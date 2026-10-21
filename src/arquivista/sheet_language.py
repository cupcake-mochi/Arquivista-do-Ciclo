"""Only presentation is translated; IDs, markers and stored status codes remain stable."""
from __future__ import annotations
import re

LABELS = {'ID do registro':'Record ID','ID Discord':'Discord ID','Justificativa':'Reason','Nº': 'No.', 'Aparência': 'Appearance', 'Nome no servidor': 'Server character name', 'Obra de origem': 'Source work', 'Situação': 'Status', 'Cadastro': 'Registered', 'Imagem': 'Image', 'Link da imagem': 'Image URL', 'Dono': 'Owner', 'Revisão': 'Revision', 'Em preparação': 'In preparation', 'Em uso': 'In use', 'Arquivado': 'Archived', 'Liberado': 'Released', 'CATÁLOGO DE APARÊNCIAS': 'APPEARANCE CATALOG', 'Edite as fichas aqui ou pelo bot. As mudanças chegam ao Discord em cerca de 5 minutos. Use + / − para ver as justificativas. Em vermelho: aparência e obra repetidas nas fichas deste membro.': 'Edit records here or through the bot. Changes reach Discord in about 5 minutes. Use + / − to view notes. Red marks an appearance and work repeated among this member’s records.', 'Escolha o número da ficha para vê-la no visor. A aba começa com 20 posições e ganha mais 20 quando restam duas livres.': 'Choose a record number to show it in the viewer. Each tab starts with 20 slots and gains 20 more when two remain free.', 'JUSTIFICATIVA / OBSERVAÇÃO   ·   só para a staff': 'REASON / NOTES   ·   staff only', 'VISOR DO PERSONAGEM · consulta': 'CHARACTER VIEWER · read only', 'Escolher nº': 'Select no.', 'OBSERVAÇÃO / JUSTIFICATIVA · leitura': 'NOTES / REASON · read only', 'POSIÇÕES   ·   abra o + ao lado de cada ficha para ver a justificativa': 'RECORD SLOTS   ·   open + beside a record to view its notes', 'Número da posição que o visor mostra.': 'Slot number to show in the viewer.', 'Nenhuma aparência nesta posição': 'No appearance in this slot', 'Escolha uma posição válida': 'Choose a valid slot', 'Aparência: ': 'Appearance: ', 'Obra: ': 'Work: ', 'Situação: ': 'Status: ', 'Cadastro: ': 'Registered: ', 'não informado': 'not provided', 'Sem observação / justificativa.': 'No notes or reason provided.', 'COMECE AQUI': 'START HERE', 'ARQUIVISTA DO CICLO · ': 'CYCLE ARCHIVIST · ', 'Esta planilha pertence à conta do Arquivista. O e-mail informado no Discord recebe acesso de editor.': 'This spreadsheet belongs to the Archivist account. The email provided in Discord receives editor access.', 'Você pode preencher as fichas aqui ou pelo bot. O que mudar em um aparece no outro.': 'Edit records here or through the bot. Changes in either place are synchronized to the other.', 'Abra a aba de um membro e preencha uma posição vazia com Aparência, Obra e Situação.': 'Open a member tab and fill an empty slot with Appearance, Source work and Status.', 'Para abrir uma aba para outra pessoa, use /planilha membro no Discord e selecione o @membro.': 'To prepare another member’s tab, use /planilha membro in Discord and select the @member.', 'Campos editáveis: aparência, nome no servidor, obra, situação, data, link da imagem e justificativa.': 'Editable fields: appearance, server character name, source work, status, date, image URL and notes.', 'Use as posições prontas. Não apague nem insira linhas; preserve as colunas de identificação e as fórmulas.': 'Use the prepared slots. Do not delete or insert rows; preserve identity columns and formulas.', 'O que você editar aqui chega ao bot em cerca de 5 minutos. Se algum dado for recusado, veja o motivo no /diagnostico.': 'Edits reach the bot in about 5 minutes. If a value is rejected, check /diagnostico for the reason.', 'Para remover um cadastro, use /remover no Discord. Limpar uma linha não apaga o cadastro do bot.': 'Remove records through /remover in Discord. Clearing a row does not delete its record from the bot.', 'Compartilhe edição somente com a staff: quem edita a planilha pode alterar os cadastros do servidor.': 'Share editor access only with staff: spreadsheet editors can change the server’s records.'}
STATUSES = {k:LABELS[k] for k in ("Em preparação","Em uso","Arquivado","Liberado")}


def label(text, language="pt-BR"):
    return LABELS.get(text,text) if language == "en" else text


def status_in(text, language="pt-BR"):
    if language == "en":
        return {v:k for k,v in STATUSES.items()}.get(text,text)
    return text


def formula(text, language="pt-BR"):
    if language != "en":
        return text
    def replace(m):
        value=m.group(1).replace('""','"')
        if value == "dd/mm/yyyy":
            value="yyyy-mm-dd"
        elif value.startswith("<>"):
            value="<>"+label(value[2:],language)
        else:
            value=label(value,language)
        return '"'+value.replace('"','""')+'"'
    return re.sub(r'"((?:[^"]|"")*)"',replace,text)
