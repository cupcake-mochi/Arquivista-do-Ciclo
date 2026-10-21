"""English product guidance; record content and stored status codes are not translated."""
from .docs import DATA_LINKS, SETUP_LINK

LINKS=DATA_LINKS.replace('Política de privacidade','Privacy policy').replace('Privacidade','Privacy').replace('Termos de uso','Terms of use').replace('Código da planilha','Spreadsheet source')
HELP='''**Browse the archive**
`AC:appearances [appearance] [@member]` or `/aparencias` — browse the list. Choose **View gallery** for pictures.
`AC:mine` shows your records; `AC:gallery` opens the gallery.
`AC:work [name]` or `/obra` searches by source work, including abbreviations and small spelling errors. Without a name it lists works.

`AC:guide` or `/guia` is the starting walkthrough.

**Your records**
`AC:register` or `/registrar` — fill in a form, review it and confirm.
`AC:edit appearance` or `/editar` — change your server character name or image.
`AC:remove appearance` or `/remover` — remove your own record after confirmation.

Portuguese commands and short names still work. The prefix is case-insensitive. Native slash-menu names follow your Discord client's language; server settings control responses. Status and notes are never shown in public searches.'''+ '\n\n'+LINKS
STAFF_HELP='''

**Staff**
`AC:register @member` registers for someone else.
`AC:status_change appearance` changes internal status and notes.
`AC:transfer appearance @member` transfers ownership, preserving ID and original date.
Staff may also remove other people's records. `AC:clear @member` removes all of a person's records; a former member's ID is accepted. With no target it lists former members with records.
`AC:alias JJK = Jujutsu Kaisen` adds a work alias; `AC:alias -JJK` removes it; no arguments lists aliases.
`AC:history [appearance]` opens private history, including removed records. `AC:diagnostics` shows archive, channel and spreadsheet health.
`/language` or `/idioma` sets this server's language. Manage Server or a configured staff role is required. New spreadsheets use the selected language; existing files keep theirs.

**Server management**
`AC:settings` or `/configurar` sets staff roles, channels, backup frequency and spreadsheet connection.
`/restaurar` with an attached JSON backup restores records after a reviewed confirmation.
`/planilha criar` privately asks for a Google editor email and delivers a ready spreadsheet. Repeating it reuses the existing file.
`/planilha abrir` or `AC:spreadsheet` reopens the link and private panel.
`/planilha membro` prepares a selected real server member's tab for manual input.
'''+ '\n'+SETUP_LINK
GUIDE=(
('What the archive records', '''The archive records who uses each **appearance**: the source character or person represented in this server, together with their **source work**.

One appearance-and-work combination may be occupied by only one person at a time. Check the list before choosing; saving also checks whether it is already taken.

Use **Next** to continue.\n\n'''+LINKS),
('Browse records', '''`AC:appearances Takao` or `/aparencias` searches by name and shows the owner. Small spelling errors are supported.
`AC:gallery` shows one record per page with its picture.
`AC:work arknights` or `/obra` groups records by work, including alternate spellings.
`AC:appearances @member` shows someone's records; `AC:mine` shows yours.

If nothing matches, try the work name too: the appearance may use another spelling.'''),
('Register your appearance', '''`AC:register` or `/registrar` opens a form:
• **Appearance:** source character's name.
• **Source work:** where they come from.
• **Server character name** (optional): their name here, shown in public lists and galleries.
• **Image:** HTTPS link or attachment.

Review the private preview, select a status, then choose **Confirm and save**. The default is **In preparation**. If occupied, the bot tells you without saving another record.'''),
('Change your record', '''`AC:edit name` or `/editar` changes your server character name or image. Enter `-` to remove the image.

`AC:remove name` or `/remover` removes your own record after confirmation. The appearance becomes available, while history stays accessible to staff.

Only staff can change appearance, source work or status after registration. Editing or removing another person's record also requires staff access.'''),
('Understand statuses', '''**In preparation:** reserved while being prepared.
**In use:** currently used.
**Archived:** no longer in use, but still occupied.
**Released:** available for someone else.

Status and notes appear only in private panels, never public lists. Stored status codes stay unchanged internally so language changes do not alter ownership or availability.'''),
('Staff review and actions', '''`AC:status_change name` changes internal status and notes. `AC:transfer name @member` changes ownership.
`AC:remove name` removes one record. `AC:clear @member` removes all of a person's records; a former member's ID is accepted.
`AC:alias JJK = Jujutsu Kaisen` adds a work-search alias.
`AC:history` shows recent changes, including removed records. `AC:diagnostics` checks the bot and spreadsheet.

Before transferring, removing or changing status, review the selected record and confirm. History is preserved.

`/language` or `/idioma` changes the language for this server. Configured staff roles and members with Manage Server may use it. The Guides bot has its own independent setting.'''),
('Configure the server and spreadsheet', '''`/configurar` requires server ownership, Administrator or Manage Server. It configures staff roles, history and image channels, spreadsheet connection, and automatic backup in a staff-only channel.

Use `/planilha criar` and enter a Google email privately. The bot provides an editable ready-made file. Reopen it with `/planilha abrir` or `AC:spreadsheet`. Use `/planilha membro` and select a server member to prepare another tab.

Fill prepared slots. Sheets edits reach the bot in about 5 minutes. Share editor access only with staff. New files use the server language selected at creation; existing files keep their original language when the server setting changes.

In **Backup**, select a channel and frequency. **Back up now** sends a copy immediately. Attach its JSON to `/restaurar` to restore records after confirmation.

The bot needs **Manage Webhooks** to send messages with Amiya's picture.\n\n'''+SETUP_LINK),
)
