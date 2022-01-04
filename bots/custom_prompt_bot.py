# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from datetime import datetime
from data_models.user_profile import PageProperties

from recognizers_number import recognize_number, Culture
from recognizers_date_time import recognize_datetime

from botbuilder.core import (
    ActivityHandler,
    ConversationState,
    TurnContext,
    UserState,
    MessageFactory,
)

from data_models import ConversationFlow, Question, UserProfile
from botbuilder.schema import ChannelAccount, CardAction, ActionTypes, SuggestedActions

import urllib.error, urllib.request, urllib.parse
import json
from utilities.jira_handler import JiraHandler
import os

class ValidationResult:
    def __init__(
        self, is_valid: bool = False, value: object = None, message: str = None
    ):
        self.is_valid = is_valid
        self.value = value
        self.message = message


class CustomPromptBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        if conversation_state is None:
            raise TypeError(
                "[CustomPromptBot]: Missing parameter. conversation_state is required but None was given"
            )
        if user_state is None:
            raise TypeError(
                "[CustomPromptBot]: Missing parameter. user_state is required but None was given"
            )
        self.template_url = "http://aem.canadaeast.cloudapp.azure.com:4503/assets/json/template.json"
        self.componentUrl = "http://aem.canadaeast.cloudapp.azure.com:4503/assets/json/component.json"
        self.data = json.loads(urllib.request.urlopen(self.template_url).read().decode("UTF-8"))
        self.component_data = json.loads(urllib.request.urlopen(self.componentUrl).read().decode("UTF-8"))
        self.selected_component_index = -1
        self.component_properties_index = -1
        self.component = {}
        self.page_properties = PageProperties()
        self.conversation_state = conversation_state
        self.user_state = user_state

        self.flow_accessor = self.conversation_state.create_property("ConversationFlow")
        self.profile_accessor = self.user_state.create_property("UserProfile")


    async def on_message_activity(self, turn_context: TurnContext):
        # Get the state properties from the turn context.
        profile = await self.profile_accessor.get(turn_context, UserProfile)
        flow = await self.flow_accessor.get(turn_context, ConversationFlow)
        page_properties = await self.profile_accessor.get(turn_context, PageProperties)
        await self._fill_out_user_profile(flow, profile, turn_context, page_properties)

        # Save changes to UserState and ConversationState
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    async def _fill_out_user_profile(
        self, flow: ConversationFlow, profile: UserProfile, turn_context: TurnContext, page_properties: PageProperties
    ):
        user_input = turn_context.activity.text.strip()

        # ask for name
        if flow.last_question_asked == Question.NONE:
            await turn_context.send_activity(
                MessageFactory.text("Let's get started. What is the name of your page?")
            )
            flow.last_question_asked = Question.NAME

        # validate name then ask for path
        elif flow.last_question_asked == Question.NAME:
            validate_result = self._validate_name(user_input)
            if not validate_result.is_valid:
                await turn_context.send_activity(
                    MessageFactory.text(validate_result.message)
                )
            else:
                self.page_properties.name = validate_result.value
                await turn_context.send_activity(
                    MessageFactory.text("What is the parent path of the page?")
                )
                flow.last_question_asked = Question.PATH
        #validate path and ask for template
        elif flow.last_question_asked == Question.PATH:
            validate_result = self._validate_name(user_input)
            if not validate_result.is_valid:
                await turn_context.send_activity(
                    MessageFactory.text(validate_result.message)
                )
            else:
                self.page_properties.path = validate_result.value
                await turn_context.send_activity(
                    MessageFactory.text(f"Page will be created under **{self.page_properties.path}**")
                )
                
                actions =  []
                reply = MessageFactory.text("What is the Template you want to use for the page?")

                for item in self.data['items']:
                    actions.append(CardAction( title=item['description'],
                            type=ActionTypes.im_back,
                            value=item['title'],
                            ))
                reply.suggested_actions = SuggestedActions(
                    actions=actions)
                
                await turn_context.send_activity(
                    reply
                )
                flow.last_question_asked = Question.TEMPLATE
        
        # validate template then ask for components
        elif flow.last_question_asked == Question.TEMPLATE:
            if self.page_properties.template == None:
                self.page_properties.template = user_input
                await turn_context.send_activity(
                    MessageFactory.text(f"Page will be created using **{self.page_properties.template}** Page Template.")
                )
            
            actions =  []
            reply = MessageFactory.text("Which component do you want add in this page?")

            for item in self.component_data['items']:
                actions.append(CardAction( title=item['description'],
                        type=ActionTypes.im_back,
                        value=item['title'],
                        ))
            reply.suggested_actions = SuggestedActions(
                actions=actions)
            
            await turn_context.send_activity(
                reply
            )
            flow.last_question_asked = Question.COMPONENT

        # validate component then ask for properties of the component
        elif flow.last_question_asked == Question.COMPONENT:
            validate_result = self._validate_name(user_input)
            if not validate_result.is_valid:
                await turn_context.send_activity(
                    MessageFactory.text(validate_result.message)
                )
            else:
                self.component = {"name": validate_result.value, "properties": {}}
                res = [x for x in range(len(self.component_data['items'])) if self.component_data['items'][x]['title'] == validate_result.value]
                self.selected_component_index = res.pop()
                self.component_properties_index = self.component_properties_index + 1
                
                await turn_context.send_activity(
                    MessageFactory.text(f"Please provide the value of **{self.component_data['items'][self.selected_component_index]['elements']['properties']['value'][self.component_properties_index]}**")
                )
                
                flow.last_question_asked = Question.FIRST_QUESTION

        # validate first question and proceed with other properties input
        elif flow.last_question_asked == Question.FIRST_QUESTION:
            validate_result = self._validate_name(user_input)
            if not validate_result.is_valid:
                await turn_context.send_activity(
                    MessageFactory.text(validate_result.message)
                )
            else:
                properties = self.component_data['items'][self.selected_component_index]['elements']['properties']
                self.component['properties'][properties['value'][self.component_properties_index]] = validate_result.value
                
                self.component_properties_index = self.component_properties_index + 1
                await turn_context.send_activity(
                    MessageFactory.text(f"Please provide the value of **{properties['value'][self.component_properties_index]}**")
                )

                if len(properties['value']) == self.component_properties_index+1:
                    flow.last_question_asked = Question.LAST_QUESTION
                else:
                    flow.last_question_asked = Question.FIRST_QUESTION

        # validate first question and proceed with other properties input
        elif flow.last_question_asked == Question.LAST_QUESTION:
            validate_result = self._validate_name(user_input)
            properties = self.component_data['items'][self.selected_component_index]['elements']['properties']
            self.component['properties'][properties['value'][self.component_properties_index]] = validate_result.value
            self.page_properties.components.append(self.component)
            self.selected_component_index = -1
            self.component_properties_index = -1
            actions =  []
            reply = MessageFactory.text("Do you want to add more Component in this page?")

            reply.suggested_actions = SuggestedActions(
                    actions=[CardAction( title="Yes",
                            type=ActionTypes.im_back,
                            value="Yes",
                            ),
                            CardAction( title="No",
                            type=ActionTypes.im_back,
                            value="No",
                            ),])
            await turn_context.send_activity(
                reply
            )
            flow.last_question_asked = Question.CONFIRMATION

        # validate first question and proceed with other properties input
        elif flow.last_question_asked == Question.CONFIRMATION:
            if user_input == 'Yes':
                reply = MessageFactory.text("Ready to add another component?")

                reply.suggested_actions = SuggestedActions(
                        actions=[CardAction( title="Yes",
                                type=ActionTypes.im_back,
                                value="Yes",
                                )])
                await turn_context.send_activity(
                    reply
                )
                flow.last_question_asked = Question.TEMPLATE
            else:
                filename = self.page_properties.name + ".txt"
                f = open(filename, "a")
                f.write(json.dumps(self.page_properties.__dict__))
                f.close()
                jh = JiraHandler(filename=filename)
                issue = jh.create_ticket()
                self.page_properties = PageProperties()
                os.remove(filename)
                await turn_context.send_activity(
                    MessageFactory.text("Your Jira request no is **" + issue +"**. Have a nice day")
                )
                flow.last_question_asked = Question.NONE

    def _validate_name(self, user_input: str) -> ValidationResult:
        if not user_input:
            return ValidationResult(
                is_valid=False,
                message="Please enter a name that contains at least one character.",
            )

        return ValidationResult(is_valid=True, value=user_input)

    def _validate_age(self, user_input: str) -> ValidationResult:
        # Attempt to convert the Recognizer result to an integer. This works for "a dozen", "twelve", "12", and so on.
        # The recognizer returns a list of potential recognition results, if any.
        results = recognize_number(user_input, Culture.English)
        for result in results:
            if "value" in result.resolution:
                age = int(result.resolution["value"])
                if 18 <= age <= 120:
                    return ValidationResult(is_valid=True, value=age)

        return ValidationResult(
            is_valid=False, message="Please enter an age between 18 and 120."
        )

    def _validate_date(self, user_input: str) -> ValidationResult:
        try:
            # Try to recognize the input as a date-time. This works for responses such as "11/14/2018", "9pm",
            # "tomorrow", "Sunday at 5pm", and so on. The recognizer returns a list of potential recognition results,
            # if any.
            results = recognize_datetime(user_input, Culture.English)
            for result in results:
                for resolution in result.resolution["values"]:
                    if "value" in resolution:
                        now = datetime.now()

                        value = resolution["value"]
                        if resolution["type"] == "date":
                            candidate = datetime.strptime(value, "%Y-%m-%d")
                        elif resolution["type"] == "time":
                            candidate = datetime.strptime(value, "%H:%M:%S")
                            candidate = candidate.replace(
                                year=now.year, month=now.month, day=now.day
                            )
                        else:
                            candidate = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

                        # user response must be more than an hour out
                        diff = candidate - now
                        if diff.total_seconds() >= 3600:
                            return ValidationResult(
                                is_valid=True,
                                value=candidate.strftime("%m/%d/%y"),
                            )

            return ValidationResult(
                is_valid=False,
                message="I'm sorry, please enter a date at least an hour out.",
            )
        except ValueError:
            return ValidationResult(
                is_valid=False,
                message="I'm sorry, I could not interpret that as an appropriate "
                "date. Please enter a date at least an hour out.",
            )
