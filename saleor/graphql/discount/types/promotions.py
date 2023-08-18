import graphene
from graphene import relay

from ....discount import PromotionEvents as events
from ....discount import models
from ....permission.auth_filters import AuthorizationFilters
from ....permission.enums import AccountPermissions, AppPermission
from ...account.dataloaders import UserByUserIdLoader
from ...account.utils import check_is_owner_or_has_one_of_perms
from ...app.dataloaders import AppByIdLoader
from ...channel.types import Channel
from ...core import ResolveInfo
from ...core.connection import CountableConnection
from ...core.descriptions import ADDED_IN_315, PREVIEW_FEATURE
from ...core.doc_category import DOC_CATEGORY_DISCOUNTS
from ...core.fields import PermissionsField
from ...core.scalars import JSON, PositiveDecimal
from ...core.types import ModelObjectType, NonNullList
from ...core.types.user_or_app import UserOrApp
from ...meta.types import ObjectWithMetadata
from ...translations.fields import TranslationField
from ...translations.types import PromotionRuleTranslation, PromotionTranslation
from ...utils import get_user_or_app_from_context
from ..dataloaders import (
    ChannelsByPromotionRuleIdLoader,
    PromotionByIdLoader,
    PromotionEventsByPromotionIdLoader,
    PromotionRulesByPromotionIdLoader,
)
from ..enums import PromotionEventsEnum, RewardValueTypeEnum


class Promotion(ModelObjectType[models.Promotion]):
    id = graphene.GlobalID(required=True)
    name = graphene.String(required=True, description="Name of the promotion.")
    description = JSON(description="Description of the promotion.")
    start_date = graphene.DateTime(
        required=True, description="Start date of the promotion."
    )
    end_date = graphene.DateTime(description="End date of the promotion.")
    created_at = graphene.DateTime(
        required=True, description="Date time of promotion creation."
    )
    updated_at = graphene.DateTime(
        required=True, description="Date time of last update of promotion."
    )
    rules = NonNullList(
        lambda: PromotionRule, description="The list of promotion rules."
    )
    translation = TranslationField(PromotionTranslation, type_name="promotion")
    events = NonNullList(
        lambda: PromotionEvent,
        description="The list of events associated with the promotion.",
    )

    class Meta:
        description = (
            "Represents the promotion that allow creating discounts based on given "
            "conditions, and is visible to all the customers."
            + ADDED_IN_315
            + PREVIEW_FEATURE
        )
        interfaces = [relay.Node, ObjectWithMetadata]
        model = models.Promotion
        doc_category = DOC_CATEGORY_DISCOUNTS

    @staticmethod
    def resolve_rules(root: models.Promotion, info: ResolveInfo):
        return PromotionRulesByPromotionIdLoader(info.context).load(root.id)

    @staticmethod
    def resolve_events(root: models.Promotion, info: ResolveInfo):
        return PromotionEventsByPromotionIdLoader(info.context).load(root.id)


class PromotionRule(ModelObjectType[models.PromotionRule]):
    id = graphene.GlobalID(required=True)
    name = graphene.String(description="Name of the promotion rule.")
    description = JSON(description="Description of the promotion rule.")
    promotion = graphene.Field(
        Promotion, description="Promotion to which the rule belongs."
    )
    channels = PermissionsField(
        NonNullList(Channel),
        description="List of channels where the rule applies.",
        permissions=[
            AuthorizationFilters.AUTHENTICATED_APP,
            AuthorizationFilters.AUTHENTICATED_STAFF_USER,
        ],
    )
    reward_value_type = RewardValueTypeEnum(
        description="The type of reward value of the promotion rule."
    )
    catalogue_predicate = JSON(
        description=(
            "The catalogue predicate that must be met to apply the rule reward."
        ),
    )
    reward_value = PositiveDecimal(
        description=(
            "The reward value of the promotion rule. Defines the discount value "
            "applied when the rule conditions are met."
        )
    )
    translation = TranslationField(PromotionRuleTranslation, type_name="promotion rule")

    class Meta:
        description = (
            "Represents the promotion rule that specifies the conditions that must "
            "be met to apply the promotion discount." + ADDED_IN_315 + PREVIEW_FEATURE
        )
        interfaces = [relay.Node]
        model = models.PromotionRule
        doc_category = DOC_CATEGORY_DISCOUNTS

    @staticmethod
    def resolve_promotion(root: models.PromotionRule, info: ResolveInfo):
        return PromotionByIdLoader(info.context).load(root.promotion_id)

    @staticmethod
    def resolve_channels(root: models.PromotionRule, info: ResolveInfo):
        return ChannelsByPromotionRuleIdLoader(info.context).load(root.id)


class PromotionCountableConnection(CountableConnection):
    class Meta:
        doc_category = DOC_CATEGORY_DISCOUNTS
        node = Promotion


def resolve_event_type(root: models.PromotionEvent, info):
    return root.type


class PromotionEvent(graphene.Interface):
    id = graphene.GlobalID()
    date = graphene.DateTime(description="Date when event happened.", required=True)
    type = PromotionEventsEnum(
        description="Promotion event type.", resolver=resolve_event_type, required=True
    )
    created_by = PermissionsField(
        UserOrApp,
        description="User or App that created the promotion event. ",
        permissions=[AccountPermissions.MANAGE_STAFF, AppPermission.MANAGE_APPS],
    )

    class Meta:
        model = models.PromotionEvent

    @staticmethod
    def resolve_type(instance: models.PromotionEvent, _info):
        return PROMOTION_EVENT_MAP.get(instance.type)

    @staticmethod
    def resolve_created_by(root: models.PromotionEvent, info):
        requester = get_user_or_app_from_context(info.context)
        if not requester:
            return None

        def _resolve_user(user):
            check_is_owner_or_has_one_of_perms(
                requester,
                user,
                AccountPermissions.MANAGE_STAFF,
            )
            return user

        def _resolve_app(app):
            check_is_owner_or_has_one_of_perms(
                requester,
                app,
                AppPermission.MANAGE_APPS,
            )
            return app

        if root.user_id:
            return (
                UserByUserIdLoader(info.context).load(root.user_id).then(_resolve_user)
            )
        if root.app_id:
            return AppByIdLoader(info.context).load(root.app_id).then(_resolve_app)

        return None


class PromotionCreatedEvent(ModelObjectType[models.PromotionEvent]):
    class Meta:
        description = (
            "History log of the promotion created event."
            + ADDED_IN_315
            + PREVIEW_FEATURE
        )
        interfaces = [relay.Node, PromotionEvent]
        model = models.PromotionEvent
        doc_category = DOC_CATEGORY_DISCOUNTS


class PromotionUpdatedEvent(ModelObjectType[models.PromotionEvent]):
    class Meta:
        description = (
            "History log of the promotion updated event."
            + ADDED_IN_315
            + PREVIEW_FEATURE
        )
        interfaces = [relay.Node, PromotionEvent]
        model = models.PromotionEvent
        doc_category = DOC_CATEGORY_DISCOUNTS


class PromotionStartedEvent(ModelObjectType[models.PromotionEvent]):
    class Meta:
        description = (
            "History log of the promotion started event."
            + ADDED_IN_315
            + PREVIEW_FEATURE
        )
        interfaces = [relay.Node, PromotionEvent]
        model = models.PromotionEvent
        doc_category = DOC_CATEGORY_DISCOUNTS


class PromotionEndedEvent(ModelObjectType[models.PromotionEvent]):
    class Meta:
        description = (
            "History log of the promotion ended event." + ADDED_IN_315 + PREVIEW_FEATURE
        )
        interfaces = [relay.Node, PromotionEvent]
        model = models.PromotionEvent
        doc_category = DOC_CATEGORY_DISCOUNTS


class PromotionRuleEvent(graphene.Interface):
    class Meta:
        description = (
            "History log of the promotion event related to rule."
            + ADDED_IN_315
            + PREVIEW_FEATURE
        )
        interfaces = [relay.Node]
        model = models.PromotionEvent
        doc_category = DOC_CATEGORY_DISCOUNTS

    rule_id = graphene.String(
        description="The rule ID associated with the promotion event."
    )

    @staticmethod
    def resolve_rule_id(root: models.PromotionEvent, _info):
        return root.parameters.get("rule_id", None)


class PromotionRuleCreatedEvent(ModelObjectType[models.PromotionEvent]):
    class Meta:
        description = (
            "History log of the promotion rule created event."
            + ADDED_IN_315
            + PREVIEW_FEATURE
        )
        interfaces = [relay.Node, PromotionEvent, PromotionRuleEvent]
        model = models.PromotionEvent
        doc_category = DOC_CATEGORY_DISCOUNTS


class PromotionRuleUpdatedEvent(ModelObjectType[models.PromotionEvent]):
    class Meta:
        description = (
            "History log of the promotion rule created event."
            + ADDED_IN_315
            + PREVIEW_FEATURE
        )
        interfaces = [relay.Node, PromotionEvent, PromotionRuleEvent]
        model = models.PromotionEvent
        doc_category = DOC_CATEGORY_DISCOUNTS


class PromotionRuleDeletedEvent(ModelObjectType[models.PromotionEvent]):
    class Meta:
        description = (
            "History log of the promotion rule created event."
            + ADDED_IN_315
            + PREVIEW_FEATURE
        )
        interfaces = [relay.Node, PromotionEvent, PromotionRuleEvent]
        model = models.PromotionEvent
        doc_category = DOC_CATEGORY_DISCOUNTS


PROMOTION_EVENT_MAP = {
    events.PROMOTION_CREATED: PromotionCreatedEvent,
    events.PROMOTION_UPDATED: PromotionUpdatedEvent,
    events.PROMOTION_STARTED: PromotionStartedEvent,
    events.PROMOTION_ENDED: PromotionEndedEvent,
    events.RULE_CREATED: PromotionRuleCreatedEvent,
    events.RULE_UPDATED: PromotionRuleUpdatedEvent,
    events.RULE_DELETED: PromotionRuleDeletedEvent,
}


class UnionPromotionEvent(graphene.Union):
    class Meta:
        types = [v for v in PROMOTION_EVENT_MAP.values()]

    @classmethod
    def resolve_type(cls, instance: models.PromotionEvent, _info):
        return PROMOTION_EVENT_MAP.get(instance.type)
