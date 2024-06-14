import json
import os
import unittest

import aiounittest
from aiohttp import ClientSession
from aioresponses import aioresponses

from yalexs.activity import (
    ACTION_BRIDGE_OFFLINE,
    ACTION_BRIDGE_ONLINE,
    ACTION_DOOR_CLOSE_2,
    ACTION_DOOR_CLOSED,
    ACTION_DOOR_OPEN,
    ACTION_DOOR_OPEN_2,
    ACTION_DOORBELL_BUTTON_PUSHED,
    ACTION_DOORBELL_CALL_HANGUP,
    ACTION_DOORBELL_CALL_INITIATED,
    ACTION_DOORBELL_CALL_MISSED,
    ACTION_DOORBELL_IMAGE_CAPTURE,
    ACTION_DOORBELL_MOTION_DETECTED,
    ACTION_HOMEKEY_LOCK,
    ACTION_HOMEKEY_UNLATCH,
    ACTION_HOMEKEY_UNLOCK,
    ACTION_LOCK_AUTO_LOCK,
    ACTION_LOCK_BLE_LOCK,
    ACTION_LOCK_BLE_UNLATCH,
    ACTION_LOCK_BLE_UNLOCK,
    ACTION_LOCK_DOORBELL_BUTTON_PUSHED,
    ACTION_LOCK_JAMMED,
    ACTION_LOCK_LOCK,
    ACTION_LOCK_LOCKING,
    ACTION_LOCK_MANUAL_LOCK,
    ACTION_LOCK_MANUAL_UNLATCH,
    ACTION_LOCK_MANUAL_UNLOCK,
    ACTION_LOCK_ONETOUCHLOCK,
    ACTION_LOCK_ONETOUCHLOCK_2,
    ACTION_LOCK_PIN_UNLATCH,
    ACTION_LOCK_PIN_UNLOCK,
    ACTION_LOCK_REMOTE_LOCK,
    ACTION_LOCK_REMOTE_UNLATCH,
    ACTION_LOCK_REMOTE_UNLOCK,
    ACTION_LOCK_UNLATCH,
    ACTION_LOCK_UNLATCHING,
    ACTION_LOCK_UNLOCK,
    ACTION_LOCK_UNLOCKING,
    ACTION_RF_LOCK,
    ACTION_RF_SECURE,
    ACTION_RF_UNLATCH,
    ACTION_RF_UNLOCK,
    ACTIVITY_ACTION_STATES,
    ACTIVITY_ACTIONS_BRIDGE_OPERATION,
    ACTIVITY_ACTIONS_DOOR_OPERATION,
    ACTIVITY_ACTIONS_DOORBELL_DING,
    ACTIVITY_ACTIONS_DOORBELL_IMAGE_CAPTURE,
    ACTIVITY_ACTIONS_DOORBELL_MOTION,
    ACTIVITY_ACTIONS_DOORBELL_VIEW,
    ACTIVITY_ACTIONS_LOCK_OPERATION,
    SOURCE_LOG,
    ActivityType,
    DoorbellDingActivity,
    LockOperationActivity,
)
from yalexs.api_async import ApiAsync
from yalexs.api_common import API_GET_LOCK_URL, ApiCommon
from yalexs.const import DEFAULT_BRAND
from yalexs.lock import LockDoorStatus, LockStatus

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"


def load_fixture(filename):
    """Load a fixture."""
    path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(path) as fptr:
        return fptr.read()


class TestActivity(unittest.TestCase):
    def test_activity_action_states(self):
        self.assertIs(
            ACTIVITY_ACTION_STATES[ACTION_LOCK_ONETOUCHLOCK], LockStatus.LOCKED
        )
        self.assertIs(ACTIVITY_ACTION_STATES[ACTION_LOCK_LOCK], LockStatus.LOCKED)
        self.assertIs(ACTIVITY_ACTION_STATES[ACTION_LOCK_UNLATCH], LockStatus.UNLATCHED)
        self.assertIs(ACTIVITY_ACTION_STATES[ACTION_LOCK_UNLOCK], LockStatus.UNLOCKED)
        self.assertIs(ACTIVITY_ACTION_STATES[ACTION_DOOR_CLOSED], LockDoorStatus.CLOSED)
        self.assertIs(ACTIVITY_ACTION_STATES[ACTION_DOOR_OPEN], LockDoorStatus.OPEN)

    def test_activity_actions(self):
        self.assertCountEqual(
            ACTIVITY_ACTIONS_DOORBELL_DING,
            [
                ACTION_DOORBELL_BUTTON_PUSHED,
                ACTION_DOORBELL_CALL_MISSED,
                ACTION_DOORBELL_CALL_HANGUP,
                ACTION_LOCK_DOORBELL_BUTTON_PUSHED,
            ],
        )
        self.assertCountEqual(
            ACTIVITY_ACTIONS_DOORBELL_MOTION,
            [ACTION_DOORBELL_MOTION_DETECTED],
        )
        self.assertCountEqual(
            ACTIVITY_ACTIONS_DOORBELL_IMAGE_CAPTURE,
            [ACTION_DOORBELL_IMAGE_CAPTURE],
        )
        self.assertCountEqual(
            ACTIVITY_ACTIONS_DOORBELL_VIEW, [ACTION_DOORBELL_CALL_INITIATED]
        )
        self.assertCountEqual(
            ACTIVITY_ACTIONS_LOCK_OPERATION,
            [
                ACTION_RF_SECURE,
                ACTION_RF_LOCK,
                ACTION_RF_UNLATCH,
                ACTION_RF_UNLOCK,
                ACTION_LOCK_AUTO_LOCK,
                ACTION_LOCK_ONETOUCHLOCK,
                ACTION_LOCK_ONETOUCHLOCK_2,
                ACTION_LOCK_LOCK,
                ACTION_LOCK_UNLATCH,
                ACTION_LOCK_UNLOCK,
                ACTION_LOCK_LOCKING,
                ACTION_LOCK_UNLATCHING,
                ACTION_LOCK_UNLOCKING,
                ACTION_HOMEKEY_LOCK,
                ACTION_HOMEKEY_UNLATCH,
                ACTION_HOMEKEY_UNLOCK,
                ACTION_LOCK_JAMMED,
                ACTION_LOCK_BLE_LOCK,
                ACTION_LOCK_BLE_UNLATCH,
                ACTION_LOCK_BLE_UNLOCK,
                ACTION_LOCK_REMOTE_LOCK,
                ACTION_LOCK_REMOTE_UNLATCH,
                ACTION_LOCK_REMOTE_UNLOCK,
                ACTION_LOCK_PIN_UNLATCH,
                ACTION_LOCK_PIN_UNLOCK,
                ACTION_LOCK_MANUAL_LOCK,
                ACTION_LOCK_MANUAL_UNLATCH,
                ACTION_LOCK_MANUAL_UNLOCK,
            ],
        )
        self.assertCountEqual(
            ACTIVITY_ACTIONS_DOOR_OPERATION,
            [
                ACTION_DOOR_CLOSED,
                ACTION_DOOR_OPEN,
                ACTION_DOOR_OPEN_2,
                ACTION_DOOR_CLOSE_2,
            ],
        )
        self.assertCountEqual(
            ACTIVITY_ACTIONS_BRIDGE_OPERATION,
            [ACTION_BRIDGE_ONLINE, ACTION_BRIDGE_OFFLINE],
        )

    def test_auto_unlock_activity(self):
        auto_unlock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("auto_unlock_activity.json"))
        )
        assert auto_unlock_activity.activity_type == ActivityType.LOCK_OPERATION
        assert auto_unlock_activity.operated_by == "My Name"
        assert auto_unlock_activity.operated_remote is False
        assert auto_unlock_activity.operated_keypad is False
        assert auto_unlock_activity.operated_manual is False
        assert auto_unlock_activity.operated_tag is False

    def test_bluetooth_lock_activity(self):
        bluetooth_lock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("bluetooth_lock_activity.json"))
        )
        assert bluetooth_lock_activity.operated_by == "I have a picture"
        assert bluetooth_lock_activity.operated_remote is False
        assert bluetooth_lock_activity.operated_keypad is False
        assert bluetooth_lock_activity.operated_manual is False
        assert bluetooth_lock_activity.operated_tag is False
        assert bluetooth_lock_activity.operator_image_url == "https://image.url"
        assert bluetooth_lock_activity.operator_thumbnail_url == "https://thumbnail.url"

    def test_keypad_lock_activity(self):
        keypad_lock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("keypad_lock_activity.json"))
        )
        assert keypad_lock_activity.operated_by == "My Name"
        assert keypad_lock_activity.operated_remote is False
        assert keypad_lock_activity.operated_keypad is True
        assert keypad_lock_activity.operated_manual is False
        assert keypad_lock_activity.operated_tag is False
        assert keypad_lock_activity.operator_image_url is None
        assert keypad_lock_activity.operator_thumbnail_url is None

    def test_auto_lock_activity(self):
        auto_lock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("auto_lock_activity.json"))
        )
        assert auto_lock_activity.operated_by == "Auto Lock"
        assert auto_lock_activity.operated_remote is False
        assert auto_lock_activity.operated_keypad is False
        assert auto_lock_activity.operated_manual is False
        assert auto_lock_activity.operated_tag is False
        assert (
            auto_lock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/auto_lock@3x.png"
        )
        assert (
            auto_lock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/auto_lock@3x.png"
        )

    def test_pin_unlock_activity(self):
        keypad_lock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("pin_unlock_activity.json"))
        )
        assert keypad_lock_activity.operated_by == "Sample Person"
        assert keypad_lock_activity.operated_remote is False
        assert keypad_lock_activity.operated_keypad is True
        assert keypad_lock_activity.operated_manual is False
        assert keypad_lock_activity.operated_tag is False
        assert (
            keypad_lock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/pin_unlock@3x.png"
        )
        assert (
            keypad_lock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/pin_unlock@3x.png"
        )

    def test_pin_unlock_activity_with_image(self):
        keypad_lock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("pin_unlock_activity_with_image.json"))
        )
        assert keypad_lock_activity.operated_by == "Zip Zoo"
        assert keypad_lock_activity.operated_remote is False
        assert keypad_lock_activity.operated_keypad is True
        assert keypad_lock_activity.operated_manual is False
        assert keypad_lock_activity.operated_tag is False
        assert (
            keypad_lock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/user/abc.jpg"
        )
        assert (
            keypad_lock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/user/abc.jpg"
        )

    def test_remote_lock_activity(self):
        remote_lock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("remote_lock_activity.json"))
        )
        assert remote_lock_activity.operated_by == "My Name"
        assert remote_lock_activity.operated_remote is True
        assert remote_lock_activity.operated_keypad is False
        assert remote_lock_activity.operated_manual is False
        assert remote_lock_activity.operated_tag is False

    def test_remote_lock_activity_v4(self):
        remote_lock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("remote_lock_activity_v4.json"))
        )
        assert remote_lock_activity.operated_by == "89 House"
        assert remote_lock_activity.operated_remote is True
        assert remote_lock_activity.operated_keypad is False
        assert remote_lock_activity.operated_manual is False
        assert remote_lock_activity.operated_tag is False
        assert (
            remote_lock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/remote_lock@3x.png"
        )
        assert (
            remote_lock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/remote_lock@3x.png"
        )

    def test_remote_unlatch_activity_v4(self):
        remote_unlatch_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("remote_unlatch_activity_v4.json"))
        )
        assert remote_unlatch_activity.activity_type == ActivityType.LOCK_OPERATION
        assert remote_unlatch_activity.operated_by == "89 House"
        assert remote_unlatch_activity.operated_remote is True
        assert remote_unlatch_activity.operated_keypad is False
        assert remote_unlatch_activity.operated_manual is False
        assert remote_unlatch_activity.operated_tag is False
        assert (
            remote_unlatch_activity.operator_image_url
            == "https://d3osa7xy9vsc0q.cloudfront.net/app/ActivityFeedIcons/remote_unlatch@3x.png"
        )
        assert (
            remote_unlatch_activity.operator_thumbnail_url
            == "https://d3osa7xy9vsc0q.cloudfront.net/app/ActivityFeedIcons/remote_unlatch@3x.png"
        )

    def test_remote_unlock_activity_v4(self):
        remote_unlock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("remote_unlock_activity_v4.json"))
        )
        assert remote_unlock_activity.activity_type == ActivityType.LOCK_OPERATION
        assert remote_unlock_activity.operated_by == "89 House"
        assert remote_unlock_activity.operated_remote is True
        assert remote_unlock_activity.operated_keypad is False
        assert remote_unlock_activity.operated_manual is False
        assert remote_unlock_activity.operated_tag is False
        assert (
            remote_unlock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/remote_unlock@3x.png"
        )
        assert (
            remote_unlock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/remote_unlock@3x.png"
        )

    def test_remote_unlock_activity_v4_2(self):
        remote_unlock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("remote_unlock_activity_v4_2.json"))
        )
        assert remote_unlock_activity.activity_type == ActivityType.LOCK_OPERATION
        assert remote_unlock_activity.operated_by == "Zipper Zoomer"
        assert remote_unlock_activity.operated_remote is True
        assert remote_unlock_activity.operated_keypad is False
        assert remote_unlock_activity.operated_manual is False
        assert remote_unlock_activity.operated_tag is False
        assert (
            remote_unlock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/user/a45daa08-f4b0-4251-aacd-7bf5475851e5.jpg"
        )
        assert (
            remote_unlock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/user/a45daa08-f4b0-4251-aacd-7bf5475851e5.jpg"
        )

    def test_manual_lock_activity_v4(self):
        manual_lock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("manual_lock_activity.json"))
        )
        assert manual_lock_activity.operated_by == "Manual Lock"
        assert manual_lock_activity.operated_remote is False
        assert manual_lock_activity.operated_keypad is False
        assert manual_lock_activity.operated_manual is True
        assert manual_lock_activity.operated_tag is False
        assert (
            manual_lock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/manual_lock@3x.png"
        )
        assert (
            manual_lock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/manual_lock@3x.png"
        )

    def test_manual_unlatch_activity_v4(self):
        manual_unlatch_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("manual_unlatch_activity.json"))
        )
        assert manual_unlatch_activity.operated_by == "Manual Unlatch"
        assert manual_unlatch_activity.operated_remote is False
        assert manual_unlatch_activity.operated_keypad is False
        assert manual_unlatch_activity.operated_manual is True
        assert manual_unlatch_activity.operated_tag is False
        assert (
            manual_unlatch_activity.operator_image_url
            == "https://d3osa7xy9vsc0q.cloudfront.net/app/ActivityFeedIcons/unlatch@3x.png"
        )
        assert (
            manual_unlatch_activity.operator_thumbnail_url
            == "https://d3osa7xy9vsc0q.cloudfront.net/app/ActivityFeedIcons/unlatch@3x.png"
        )

    def test_manual_unlock_activity_v4(self):
        manual_unlock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("manual_unlock_activity.json"))
        )
        assert manual_unlock_activity.operated_by == "Manual Unlock"
        assert manual_unlock_activity.operated_remote is False
        assert manual_unlock_activity.operated_keypad is False
        assert manual_unlock_activity.operated_manual is True
        assert manual_unlock_activity.operated_tag is False
        assert (
            manual_unlock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/manual_unlock@3x.png"
        )
        assert (
            manual_unlock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/manual_unlock@3x.png"
        )

    def test_rf_unlock_activity_v4(self):
        rf_unlock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("rf_unlock_activity_v4.json"))
        )
        assert rf_unlock_activity.operated_by == "89 House"
        assert rf_unlock_activity.operated_remote is False
        assert rf_unlock_activity.operated_keypad is False
        assert rf_unlock_activity.operated_manual is False
        assert rf_unlock_activity.operated_tag is True
        assert (
            rf_unlock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/rf_unlock@3x.png"
        )
        assert (
            rf_unlock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/rf_unlock@3x.png"
        )

    def test_homekey_unlock_activity_v4(self):
        homekey_unlock_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("homekey_unlock_activity_v4.json"))
        )
        assert homekey_unlock_activity.operated_by == "89 House"
        assert homekey_unlock_activity.operated_remote is False
        assert homekey_unlock_activity.operated_keypad is False
        assert homekey_unlock_activity.operated_manual is False
        assert homekey_unlock_activity.operated_tag is True
        assert (
            homekey_unlock_activity.operator_image_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/homekey_unlock@3x.png"
        )
        assert (
            homekey_unlock_activity.operator_thumbnail_url
            == "https://d33mytkkohwnk6.cloudfront.net/app/ActivityFeedIcons/homekey_unlock@3x.png"
        )

    def test_lock_activity(self):
        lock_operation_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("lock_activity.json"))
        )
        assert lock_operation_activity.operated_by == "MockHouse House"
        assert lock_operation_activity.operated_remote is True
        assert lock_operation_activity.operated_keypad is False
        assert lock_operation_activity.operated_autorelock is False

    def test_unlock_activity(self):
        unlock_operation_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("unlock_activity.json"))
        )
        assert unlock_operation_activity.operated_by == "MockHouse House"
        assert unlock_operation_activity.operated_keypad is False
        assert unlock_operation_activity.operated_remote is True
        assert unlock_operation_activity.operator_image_url is None
        assert unlock_operation_activity.operated_autorelock is False
        assert unlock_operation_activity.operator_thumbnail_url is None

    def test_autorelock_activity(self):
        auto_relock_operation_activity = LockOperationActivity(
            SOURCE_LOG, json.loads(load_fixture("auto_relock_activity.json"))
        )
        assert auto_relock_operation_activity.operated_by == "I have no picture"
        assert auto_relock_operation_activity.operated_remote is False
        assert auto_relock_operation_activity.operated_autorelock is True
        assert auto_relock_operation_activity.operated_keypad is False

    def test_get_lock_button_pressed(self):
        doorbell_ding_activity = DoorbellDingActivity(
            SOURCE_LOG, json.loads(load_fixture("lock_accessory_motion_detect.json"))
        )
        assert doorbell_ding_activity.activity_start_time.timestamp() == 1691249378.0
        assert doorbell_ding_activity.activity_end_time.timestamp() == 1691249378.0


class TestActivityApiAsync(aiounittest.AsyncTestCase):
    @aioresponses()
    async def test_async_get_lock_detail_bridge_online(self, mock):
        mock.get(
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_URL)
            .format(lock_id="A6697750D607098BAE8D6BAA11EF8063"),
            body=load_fixture("get_lock.online.json"),
        )

        api = ApiAsync(ClientSession())
        await api.async_get_lock_detail(
            ACCESS_TOKEN, "A6697750D607098BAE8D6BAA11EF8063"
        )

        keypad_lock_activity = LockOperationActivity(
            SOURCE_LOG,
            json.loads(load_fixture("pin_unlock_activity_missing_image.json")),
        )
        assert keypad_lock_activity.operated_by == "Zip Zoo"
        assert keypad_lock_activity.operated_remote is False
        assert keypad_lock_activity.operated_keypad is True
        assert (
            keypad_lock_activity.operator_image_url == "https://www.image.com/foo.jpeg"
        )
        assert (
            keypad_lock_activity.operator_thumbnail_url
            == "https://www.image.com/foo.jpeg"
        )
