import logging
from logging import handlers
from django.core.management.base import BaseCommand
import traceback

from django.db import transaction

from script.utils.outgoing import check_progress
from script.models import Script
from optparse import OptionParser, make_option
from datetime import datetime
from django.core.mail import send_mail
from django.conf import settings

# Make sure a NullHandler is available
# This was added in Python 2.7/3.2
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
logger = logging.getLogger(__name__)
logging.basicConfig(filename="script.log", level=logging.DEBUG)
# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler("script.log", maxBytes=5242880, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-e", "--early", dest="e"),
        make_option("-l", "--late", dest="l")
    )

    @transaction.commit_manually
    def handle(self, **options):

        current = datetime.now()
        recipients = getattr(settings, 'ADMINS', None)
        if recipients:
            recipients = [admintuple[1] for admintuple in recipients]
        if 'e' in options and 'l' in options and not (current.hour in range(int(options['e']), int(options['l']))):
            return
        try:
            for script in Script.objects.filter(enabled=True):
                check_progress(script)
            transaction.commit()
        except Exception, exc:
            transaction.rollback()
            print traceback.format_exc(exc)
            logger.debug(str(exc))
            if recipients:
                send_mail('[Django] Error: check_script_progress cron', str(traceback.format_exc(exc)), 'root@uganda.rapidsms.org', recipients, fail_silently=True)
