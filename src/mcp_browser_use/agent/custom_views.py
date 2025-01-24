# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import List, Type

from browser_use.agent.views import AgentOutput
from browser_use.controller.registry.views import ActionModel
from pydantic import BaseModel, ConfigDict, Field, create_model


@dataclass
class CustomAgentStepInfo:
    """
    Holds metadata about a single step of the agent's execution.

    :param step_number: Which step number we're currently on.
    :param max_steps: Total maximum steps before we stop.
    :param task: The primary task assigned to the agent.
    :param add_infos: Additional contextual info or instructions.
    :param memory: Cumulative memory or context from previous steps.
    :param task_progress: Text describing progress toward the task goal.
    """

    step_number: int
    max_steps: int
    task: str
    add_infos: str
    memory: str
    task_progress: str


class CustomAgentBrain(BaseModel):
    """
    Represents the agent's 'thinking' or ephemeral state during processing.

    :param prev_action_evaluation: String evaluation of the last action performed (success/failure).
    :param important_contents: Key points or memory extracted from the environment.
    :param completed_contents: Completed portion of the task so far.
    :param thought: Agent's internal reasoning or thought process text.
    :param summary: Short summary of the agent's current state or progress.
    """

    prev_action_evaluation: str
    important_contents: str
    completed_contents: str
    thought: str
    summary: str


class CustomAgentOutput(AgentOutput):
    """
    Output model for the agent. Extended at runtime with custom actions
    by 'type_with_custom_actions'.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_state: CustomAgentBrain
    action: List[ActionModel]

    @staticmethod
    def type_with_custom_actions(
        custom_actions: Type[ActionModel],
    ) -> Type["CustomAgentOutput"]:
        """
        Create a new Pydantic model that inherits from CustomAgentOutput
        but redefines the 'action' field to be a list of the given
        custom action model.

        :param custom_actions: The action model type from the controller registry.
        :return: A new Pydantic model class based on CustomAgentOutput.
        """
        return create_model(
            # Could rename to something more specific if needed
            "AgentOutput",
            __base__=CustomAgentOutput,
            action=(List[custom_actions], Field(...)),
            __module__=CustomAgentOutput.__module__,
        )
