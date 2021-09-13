#!/usr/bin/env python

import yaml
import argparse
import hashlib
import os
import datetime
import pytz

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/calendar.events.owned"]

def create_time(date, time, timezone, all_day):
    if all_day:
        return {"date": str(date), "timeZone": timezone}

    offset = datetime.datetime.now(pytz.timezone(timezone)).strftime('%z')

    return {"dateTime": f"{date}T{time}:00{offset}", "timeZone": timezone}

def create_event_generator(service):
    def create_event(
        calendarId,
        eventId,
        name,
        start,
        end,
        loc
        ):
        event = {
            "id": eventId,
            "summary": name,
            "location": loc,
            "start": start, 
            "end": end,
        }

        event = service.events().insert(calendarId=calendarId, body=event).execute()

    return create_event

def oauth():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    return creds


def main(calendar_yaml, timezone):
    # read in yaml file
    data = yaml.load(open(calendar_yaml))

    creds = oauth()
    service = build("calendar", "v3", credentials=creds)

    # read in defaults
    default_start = data["defaults"]["start"]
    default_end = data["defaults"]["end"]
    default_loc = data["defaults"]["location"]
    default_cal = data["defaults"]["calendarId"]

    events = data["events"]

    create_event = create_event_generator(service)

    for chunk in events:
        prefix = chunk["chunk_prefix"]
        for event in chunk["events"]:
            date = event["date"]
            all_day = event.get("all_day", False)
            start = event.get("start", default_start)
            end = event.get("end", default_end)
            loc = event.get("location", default_loc)
            title = f"{prefix} {event['title']}"
            cal_id = event.get("calendarId", default_cal)

            start = create_time(date, start, timezone, all_day)
            end = create_time(date, end, timezone, all_day)

            event_id = hashlib.sha512(title.encode("utf-8")).hexdigest()

            print(title)
            print(event_id)
            print(start)
            print(end)
            print(loc)
            print(cal_id)

            try:
                create_event(cal_id, event_id, title, start, end, loc)
            except HttpError as e:
                print(e.reason)
                if e.reason == "Bad Request":
                    raise

            print()



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("calendar_yaml")
    parser.add_argument("--timezone",
        default="America/New_York")

    args = parser.parse_args()
    main(args.calendar_yaml, args.timezone)