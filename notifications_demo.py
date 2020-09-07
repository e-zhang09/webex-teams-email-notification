import json
import os
import datetime

from notification_driver import NotificationDriver

script_dir = os.path.dirname(__file__)

if __name__ == '__main__':
    # make sure to source credentials first!
    driver = NotificationDriver()

    # get logs into list
    sub_sub_component_id = 'log_id_2'
    with open(os.path.join(script_dir, 'example_log.json')) as json_file:
        logs = json.load(json_file)['logs'][-25:]  # only take last 25 logs

    # sends an email to that dest (given correct email configs)
    email_dest = str(input("""Enter a destination email: """))
    driver.send_email_logs(email_dest, logs, action_needed=True)

    # send notifications test to group
    group_name = str(input("""Enter a group chat name (make sure this bot is added to that chat first): """))
    driver.send_webex_logs_to_group(group_name, logs, action_needed=True)

    # send notifications test to a webex user with this email
    person_email = str(input("""Enter a person's webex acct email: """))
    driver.send_webex_logs_to_person(person_email, logs, action_needed=True)
