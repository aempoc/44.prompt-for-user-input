# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


from typing import List, Text


class UserProfile:
    def __init__(self, name: str = None, age: int = 0, date: str = None):
        self.name = name
        self.age = age
        self.date = date

class PageProperties:
    def __init__(self, name: str = None, path: str = None,template: str=None, components: list = []):
        self.name = name
        self.path = path
        self.template = template
        self.components = components