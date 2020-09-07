import json
import smtplib
import os
import string

import html2text
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import time
import random

from webexteamssdk import WebexTeamsAPI, webexteamssdkException, ApiError

class NotificationDriver:
    """Easily send msg via email or webex teams"""

    def __init__(self, use_email=True, use_webex=True):
        if use_email:
            try:
                smtp_server = str(os.environ['EMAIL_SMTP_SERVER']).rstrip()  # carriage return issues
                smtp_port = int(os.environ['EMAIL_SMTP_PORT'])
                smtp_sender_email = str(os.environ['EMAIL_SMTP_SENDER_EMAIL']).rstrip()
                smtp_username = str(os.environ['EMAIL_SMTP_USERNAME']).rstrip()
                smtp_password = str(os.environ['EMAIL_SMTP_PASSWORD']).rstrip()
            except KeyError as e:
                print(
                    """Please make sure EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, EMAIL_SMTP_USERNAME, and EMAIL_SMTP_PASSWORD are 
                    available in the environment (use export)""")
                raise EnvVariablesMissing
            self.smtp_server = smtp_server
            self.smtp_port = smtp_port
            self.smtp_sender_email = smtp_sender_email
            self.smtp_username = smtp_username
            self.smtp_password = smtp_password
        if use_webex:
            try:
                api = WebexTeamsAPI()
            except webexteamssdkException as e:
                print(
                    """Please make sure WEBEX_TEAMS_ACCESS_TOKEN are 
                    available in the environment (use export)""")
                raise EnvVariablesMissing
            self.webex_api = api

    def send_webex_to_room(self, room_name, mark_down, files: list = None):
        room_id = None
        rooms = self.webex_api.rooms.list()
        for room in rooms:
            if room.title == room_name:
                room_id = room.id
        if room_id == 0:
            raise RoomNotFoundError

        msg = 'failed'

        try:
            msg = self.webex_api.messages.create(roomId=room_id, markdown=mark_down, text=mark_down, files=files)
            # print(msg)
        except ApiError as err:
            print(
                """Something went wrong with Webex API"""
            )
            raise
        except Exception as exc:
            print(exc)
            raise
        finally:
            return msg

    def send_webex_to_person(self, person_email, mark_down, files=None):
        msg = 'failed'

        try:
            msg = self.webex_api.messages.create(toPersonEmail=person_email, markdown=mark_down, text=mark_down,
                                                 files=files)
            # print(msg)
        except ApiError as err:
            print(
                """Something went wrong with Webex API"""
            )
            raise
        except Exception as exc:
            print(exc)
            raise
        finally:
            return msg

    @staticmethod
    def create_tmp_logs(logs: list) -> str:
        # TODO: maybe use external path...?
        ran_filename = 'logs_' + str(str().join(random.sample(string.ascii_letters, 20))) + '.json'
        path_to_file = os.path.join('tmp', ran_filename)

        with open(path_to_file, 'w') as tmp_file:
            json.dump({"logs": logs}, tmp_file, indent=2)

        return path_to_file

    def send_webex_logs_to_person(self, person_email, logs: list, script_name="check_db.py", time_ms=0,
                                  action_needed=False):
        if not time_ms:
            time_ms = time.time() * 1000

        action_needed = "<h3>ACTION_NEEDED</h3>" if action_needed else None

        path_to_file = self.create_tmp_logs(logs)

        num_logs = len(logs)

        logs = logs[-8:]

        html = """\
        <html>
              <body>
                    {0}
                    <p>Recent Logs from <code>{1}</code> at {2} today ({3})
                    </p>
                    </br>
                    Last eight logs:</br>    
                    {4}
                    {5} more logs could be found in attached file.
              </body>
        </html>
            """.format(action_needed, script_name, get_time(time_ms), get_full_time(time_ms), self.gen_dash_li(logs),
                       num_logs)

        mark_down = self.gen_markdown(html)

        self.send_webex_to_person(person_email, mark_down, [path_to_file])

        os.remove(path_to_file)

    def send_webex_logs_to_group(self, room_name, logs: list, script_name="check_db.py", time_ms=0,
                                 action_needed=False):
        if not time_ms:
            time_ms = time.time() * 1000

        action_needed = "<h3>ACTION_NEEDED</h3>" if action_needed else None

        path_to_file = self.create_tmp_logs(logs)

        num_logs = len(logs)

        logs = logs[-5:]

        html = """\
        <html>
              <body>
                    {0}
                    <p>Recent Logs from <code>{1}</code> at {2} today ({3})
                    </p>
                    </br>
                    Last five logs:</br>
                    {4}
                    {5} more logs could be found in attached file.
              </body>
        </html>
            """.format(action_needed, script_name, get_time(time_ms), get_full_time(time_ms), self.gen_dash_li(logs),
                       num_logs)

        mark_down = self.gen_markdown(html)

        self.send_webex_to_room(room_name, mark_down, [path_to_file])

        os.remove(path_to_file)

    def send_email(self, receiver_email, message: MIMEMultipart) -> None:
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.smtp_sender_email, receiver_email, message.as_string())
        except Exception as server_error:
            print(server_error)
            raise

    def send_email_logs(self, receiver_email: str, logs: list, name: str = "Whoever It May Concern", time_ms=0,
                        subject_line="Logs from today",
                        action_needed=False) -> None:
        if not time_ms:
            time_ms = time.time() * 1000
        html = """\
        <html>
              <body>
                    <h3>Dear {0},</h3>
                    </br>
                    <p>After running <code>{1}</code> at {2} today ({3}), there were some errors that may concern you.
                    </p>
                    </br>
                    Relevant Logs:</br>
                    <ul>
                        {4}
                    <ul>
              </body>
        </html>
            """.format(name, "check_db.py", get_time(time_ms), get_full_time(time_ms), self.gen_html_li(logs))

        message = self.gen_email_message(html,
                                         '{}{}'.format(
                                             "Actions Needed! " if action_needed else "",
                                             subject_line),
                                         receiver_email)
        try:
            self.send_email(receiver_email, message)
        except Exception as e:
            raise

    def gen_email_message(self, html: str, subject_line: str, receiver_email: str) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject_line
        message["From"] = self.smtp_sender_email
        message["To"] = receiver_email
        text = html2text.html2text(html)

        # Turn these into plain/html MIMEText objects
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(part1)
        message.attach(part2)
        return message

    @staticmethod
    def gen_markdown(html: str) -> str:
        return html2text.html2text(html)

    @staticmethod
    def gen_dash_li(arr: list) -> str:
        str_builder = str()

        for log in arr:
            log_str = '[{0:%Y-%m-%d %H:%M:%S}]'.format(datetime.datetime.fromtimestamp(int(log['timestamp']) / 1000.0))

            log_str = log_str + " {"

            type_str = str()
            if log['type'] == 'error' or log['type'] == 'warning':
                type_str = "*{}*".format(log['type'])
            else:
                type_str = log['type']

            p_front = len(type_str)

            for i in range(int((9 - len(type_str)) / 2)):
                type_str = "&nbsp;" + type_str
                p_front = p_front + 1

            for j in range(9 - p_front):
                type_str = type_str + "&nbsp;"

            log_str = log_str + type_str + "} " + str(log['log'])

            str_builder += \
                "<p>- {}</p>".format(log_str)

        return str_builder

    @staticmethod
    def gen_html_li(arr: list) -> str:
        str_builder = str()

        for log in arr:
            log_str = '[{0:%Y-%m-%d %H:%M:%S}]'.format(datetime.datetime.fromtimestamp(int(log['timestamp']) / 1000.0))

            log_str = log_str + " {"

            type_str = str()
            if log['type'] == 'error' or log['type'] == 'warning':
                type_str = "*{}*".format(log['type'])
            else:
                type_str = log['type']

            p_front = len(type_str)
            for i in range(int((9 - len(type_str)) / 2)):
                type_str = "&nbsp;" + type_str
                p_front = p_front + 1

            for j in range(9 - p_front):
                type_str = type_str + "&nbsp;"

            log_str = log_str + type_str + "} " + str(log['log'])

            str_builder += \
                "<li><code>{}</code></li>".format(log_str)
        return str_builder


def get_time(milliseconds: int) -> str:
    return datetime.datetime.fromtimestamp(milliseconds / 1000.0).strftime("%I:%M %p")


def get_full_time(milliseconds: int) -> str:
    return datetime.datetime.fromtimestamp(milliseconds / 1000.0).strftime("%m/%d/%Y %H:%M:%S")


class Error(Exception):
    """Base Class"""
    pass


class RoomNotFoundError(Error):
    """Raised when the room_name supplied is not matched (is bot added to room?)"""


class PersonNotFoundError(Error):
    """Raised when the person_name supplied is not matched (does bot have conversation with that person?)"""


class EnvVariablesMissing(Error):
    """Raised when some required environmental variables are not available"""
