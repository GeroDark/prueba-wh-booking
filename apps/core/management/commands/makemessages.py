from django.core.management.commands import makemessages


class Command(makemessages.Command):
    """makemessages without fuzzy matching.

    By default msgmerge guesses translations for new strings from similar existing ones
    (e.g. "country" -> "Cuentas") and marks them fuzzy, which compilemessages then skips:
    the string silently stays untranslated. New strings should start empty instead.
    """

    msgmerge_options = [*makemessages.Command.msgmerge_options, "--no-fuzzy-matching"]
