import logging
import json

log = logging.getLogger()


def handler(event, context):
    """
    Entry-point for Serverless Function.
    :param event: request payload.
    :param context: information about current execution context.
    :return: response to be serialized as JSON.
    """
    text = "Hello! I\'ll repeat anything you say to me."
    if (
        "request" in event
        and "original_utterance" in event["request"]
        and len(event["request"]["original_utterance"]) > 0
    ):
        text = event["request"]["original_utterance"]
        if nlu := event["request"]["nlu"]:
            if intents := nlu['intents']['f']:
                if what := intents['slots']['what']["value"]:
                    text = f'Да, {what}, действительно закончилась'

            # log.warning('nlu: ' + json.dumps(event["request"]["nlu"]))

    return {
        "version": event["version"],
        "session": event["session"],
        "response": {"text": text, "end_session": True},
    }
