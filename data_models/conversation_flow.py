# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from enum import Enum


class Question(Enum):
    NAME = 1
    PATH = 2
    TEMPLATE = 3
    COMPONENT = 4
    FIRST_QUESTION = 5
    LAST_QUESTION = 6
    CONFIRMATION = 7
    DATE = 15
    NONE = 16


class ConversationFlow:
    def __init__(
        self, last_question_asked: Question = Question.NONE,
    ):
        self.last_question_asked = last_question_asked
