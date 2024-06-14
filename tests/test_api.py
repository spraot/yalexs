import os
import unittest
from datetime import datetime

import dateutil.parser
import requests_mock
from dateutil.tz import tzlocal, tzutc
from requests.exceptions import HTTPError
from requests.models import Response
from requests.structures import CaseInsensitiveDict

import yalexs.activity
from yalexs.api import Api, _raise_response_exceptions
from yalexs.api_common import (
    API_GET_DOORBELL_URL,
    API_GET_DOORBELLS_URL,
    API_GET_HOUSE_ACTIVITIES_URL,
    API_GET_LOCK_STATUS_URL,
    API_GET_LOCK_URL,
    API_GET_LOCKS_URL,
    API_GET_PINS_URL,
    API_GET_USER_URL,
    API_LOCK_URL,
    API_UNLATCH_URL,
    API_UNLOCK_URL,
    ApiCommon,
)
from yalexs.bridge import BridgeDetail, BridgeStatus, BridgeStatusDetail
from yalexs.const import DEFAULT_BRAND
from yalexs.exceptions import AugustApiHTTPError
from yalexs.lock import LockDoorStatus, LockStatus

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"


def load_fixture(filename):
    """Load a fixture."""
    path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(path) as fptr:
        return fptr.read()


def utc_of(year, month, day, hour, minute, second, microsecond):
    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tzutc())


class TestApi(unittest.TestCase):
    @requests_mock.Mocker()
    def test_get_doorbells(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND).get_brand_url(API_GET_DOORBELLS_URL),
            text=load_fixture("get_doorbells.json"),
        )

        api = Api()
        doorbells = sorted(api.get_doorbells(ACCESS_TOKEN), key=lambda d: d.device_id)

        self.assertEqual(2, len(doorbells))

        first = doorbells[0]
        self.assertEqual("1KDAbJH89XYZ", first.device_id)
        self.assertEqual("aaaaR08888", first.serial_number)
        self.assertEqual("Back Door", first.device_name)
        self.assertEqual("doorbell_call_status_offline", first.status)
        self.assertEqual(False, first.has_subscription)
        self.assertEqual(None, first.image_url)
        self.assertEqual("3dd2accadddd", first.house_id)
        self.assertEqual("", first.content_token)

        second = doorbells[1]
        self.assertEqual("K98GiDT45GUL", second.device_id)
        self.assertEqual("tBXZR0Z35E", second.serial_number)
        self.assertEqual("Front Door", second.device_name)
        self.assertEqual("doorbell_call_status_online", second.status)
        self.assertEqual(True, second.has_subscription)
        self.assertEqual("https://image.com/vmk16naaaa7ibuey7sar.jpg", second.image_url)
        self.assertEqual("3dd2accaea08", second.house_id)
        self.assertEqual("", second.content_token)

    @requests_mock.Mocker()
    def test_get_doorbell_detail(self, mock):
        expected_doorbell_image_url = "https://image.com/vmk16naaaa7ibuey7sar.jpg"
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_DOORBELL_URL)
            .format(doorbell_id="K98GiDT45GUL"),
            text=load_fixture("get_doorbell.json"),
        )
        mock.register_uri(
            "get", expected_doorbell_image_url, text="doorbell_image_mocked"
        )

        api = Api()
        doorbell = api.get_doorbell_detail(ACCESS_TOKEN, "K98GiDT45GUL")

        self.assertEqual("K98GiDT45GUL", doorbell.device_id)
        self.assertEqual("Front Door", doorbell.device_name)
        self.assertEqual("3dd2accaea08", doorbell.house_id)
        self.assertEqual("tBXZR0Z35E", doorbell.serial_number)
        self.assertEqual("2.3.0-RC153+201711151527", doorbell.firmware_version)
        self.assertEqual("doorbell_call_status_online", doorbell.status)
        self.assertEqual(96, doorbell.battery_level)
        self.assertEqual("gen1", doorbell.model)
        self.assertEqual(True, doorbell.is_online)
        self.assertEqual(False, doorbell.is_standby)
        self.assertEqual(
            dateutil.parser.parse("2017-12-10T08:01:35Z"),
            doorbell.image_created_at_datetime,
        )
        self.assertEqual(True, doorbell.has_subscription)
        self.assertEqual(expected_doorbell_image_url, doorbell.image_url)
        self.assertEqual(doorbell.get_doorbell_image(), b"doorbell_image_mocked")
        self.assertEqual(
            doorbell.get_doorbell_image(timeout=50), b"doorbell_image_mocked"
        )

    @requests_mock.Mocker()
    def test_get_doorbell_detail_missing_image(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_DOORBELL_URL)
            .format(doorbell_id="K98GiDT45GUL"),
            text=load_fixture("get_doorbell_missing_image.json"),
        )

        api = Api()
        doorbell = api.get_doorbell_detail(ACCESS_TOKEN, "K98GiDT45GUL")

        self.assertEqual("K98GiDT45GUL", doorbell.device_id)
        self.assertEqual("Front Door", doorbell.device_name)
        self.assertEqual("3dd2accaea08", doorbell.house_id)
        self.assertEqual("tBXZR0Z35E", doorbell.serial_number)
        self.assertEqual("2.3.0-RC153+201711151527", doorbell.firmware_version)
        self.assertEqual("doorbell_call_status_online", doorbell.status)
        self.assertEqual(96, doorbell.battery_level)
        self.assertEqual(True, doorbell.is_online)
        self.assertEqual(False, doorbell.is_standby)
        self.assertEqual(None, doorbell.image_created_at_datetime)
        self.assertEqual(True, doorbell.has_subscription)
        self.assertEqual(None, doorbell.image_url)

    @requests_mock.Mocker()
    def test_get_doorbell_offline(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_DOORBELL_URL)
            .format(doorbell_id="231ee2168dd0"),
            text=load_fixture("get_doorbell.offline.json"),
        )

        api = Api()
        doorbell = api.get_doorbell_detail(ACCESS_TOKEN, "231ee2168dd0")

        self.assertEqual("231ee2168dd0", doorbell.device_id)
        self.assertEqual("My Door", doorbell.device_name)
        self.assertEqual("houseid", doorbell.house_id)
        self.assertEqual("abcd", doorbell.serial_number)
        self.assertEqual("3.1.0-HYDRC75+201909251139", doorbell.firmware_version)
        self.assertEqual("doorbell_offline", doorbell.status)
        self.assertEqual(81, doorbell.battery_level)
        self.assertEqual(False, doorbell.is_online)
        self.assertEqual(False, doorbell.is_standby)
        self.assertEqual(
            dateutil.parser.parse("2019-02-20T23:52:46Z"),
            doorbell.image_created_at_datetime,
        )
        self.assertEqual(True, doorbell.has_subscription)
        self.assertEqual("https://res.cloudinary.com/x.jpg", doorbell.image_url)
        self.assertEqual("hydra1", doorbell.model)

    @requests_mock.Mocker()
    def test_get_doorbell_gen2_full_battery_detail(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_DOORBELL_URL)
            .format(doorbell_id="did"),
            text=load_fixture("get_doorbell.battery_full.json"),
        )

        api = Api()
        doorbell = api.get_doorbell_detail(ACCESS_TOKEN, "did")

        self.assertEqual(100, doorbell.battery_level)

    @requests_mock.Mocker()
    def test_get_doorbell_gen2_medium_battery_detail(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_DOORBELL_URL)
            .format(doorbell_id="did"),
            text=load_fixture("get_doorbell.battery_medium.json"),
        )

        api = Api()
        doorbell = api.get_doorbell_detail(ACCESS_TOKEN, "did")

        self.assertEqual(75, doorbell.battery_level)

    @requests_mock.Mocker()
    def test_get_doorbell_gen2_low_battery_detail(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_DOORBELL_URL)
            .format(doorbell_id="did"),
            text=load_fixture("get_doorbell.battery_low.json"),
        )

        api = Api()
        doorbell = api.get_doorbell_detail(ACCESS_TOKEN, "did")

        self.assertEqual(10, doorbell.battery_level)

    @requests_mock.Mocker()
    def test_get_locks(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND).get_brand_url(API_GET_LOCKS_URL),
            text=load_fixture("get_locks.json"),
        )

        api = Api()
        locks = sorted(api.get_locks(ACCESS_TOKEN), key=lambda d: d.device_id)

        self.assertEqual(2, len(locks))

        first = locks[0]
        self.assertEqual("A6697750D607098BAE8D6BAA11EF8063", first.device_id)
        self.assertEqual("Front Door Lock", first.device_name)
        self.assertEqual("000000000000", first.house_id)
        self.assertEqual(True, first.is_operable)

        second = locks[1]
        self.assertEqual("A6697750D607098BAE8D6BAA11EF9999", second.device_id)
        self.assertEqual("Back Door Lock", second.device_name)
        self.assertEqual("000000000011", second.house_id)
        self.assertEqual(False, second.is_operable)

    @requests_mock.Mocker()
    def test_get_operable_locks(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND).get_brand_url(API_GET_LOCKS_URL),
            text=load_fixture("get_locks.json"),
        )

        api = Api()
        locks = api.get_operable_locks(ACCESS_TOKEN)

        self.assertEqual(1, len(locks))

        first = locks[0]
        self.assertEqual("A6697750D607098BAE8D6BAA11EF8063", first.device_id)
        self.assertEqual("Front Door Lock", first.device_name)
        self.assertEqual("000000000000", first.house_id)
        self.assertEqual(True, first.is_operable)

    @requests_mock.Mocker()
    def test_get_lock_detail_with_doorsense_bridge_online(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_URL)
            .format(lock_id="ABC"),
            text=load_fixture("get_lock.online_with_doorsense.json"),
        )

        api = Api()
        lock = api.get_lock_detail(ACCESS_TOKEN, "ABC")

        self.assertEqual("ABC", lock.device_id)
        self.assertEqual("Online door with doorsense", lock.device_name)
        self.assertEqual("123", lock.house_id)
        self.assertEqual("XY", lock.serial_number)
        self.assertEqual("undefined-4.3.0-1.8.14", lock.firmware_version)
        self.assertEqual(92, lock.battery_level)
        self.assertEqual("AUG-MD01", lock.model)
        self.assertEqual(None, lock.keypad)
        self.assertIsInstance(lock.bridge, BridgeDetail)
        self.assertIsInstance(lock.bridge.status, BridgeStatusDetail)
        self.assertEqual(BridgeStatus.ONLINE, lock.bridge.status.current)
        self.assertEqual(True, lock.bridge_is_online)
        self.assertEqual(True, lock.bridge.operative)
        self.assertEqual(True, lock.doorsense)

        self.assertEqual(LockStatus.LOCKED, lock.lock_status)
        self.assertEqual(LockDoorStatus.OPEN, lock.door_state)
        self.assertEqual(
            dateutil.parser.parse("2017-12-10T04:48:30.272Z"), lock.lock_status_datetime
        )
        self.assertEqual(
            dateutil.parser.parse("2017-12-10T04:48:30.272Z"), lock.door_state_datetime
        )

    @requests_mock.Mocker()
    def test_get_lock_detail_bridge_online(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_URL)
            .format(lock_id="A6697750D607098BAE8D6BAA11EF8063"),
            text=load_fixture("get_lock.online.json"),
        )

        api = Api()
        lock = api.get_lock_detail(ACCESS_TOKEN, "A6697750D607098BAE8D6BAA11EF8063")

        self.assertEqual("A6697750D607098BAE8D6BAA11EF8063", lock.device_id)
        self.assertEqual("Front Door Lock", lock.device_name)
        self.assertEqual("000000000000", lock.house_id)
        self.assertEqual("X2FSW05DGA", lock.serial_number)
        self.assertEqual("109717e9-3.0.44-3.0.30", lock.firmware_version)
        self.assertEqual(88, lock.battery_level)
        self.assertEqual("AUG-SL02-M02-S02", lock.model)
        self.assertEqual("Medium", lock.keypad.battery_level)
        self.assertEqual(60, lock.keypad.battery_percentage)
        self.assertEqual("5bc65c24e6ef2a263e1450a8", lock.keypad.device_id)
        self.assertIsInstance(lock.bridge, BridgeDetail)
        self.assertEqual(True, lock.bridge_is_online)
        self.assertEqual(True, lock.bridge.operative)
        self.assertEqual(True, lock.doorsense)

        self.assertEqual(LockStatus.LOCKED, lock.lock_status)
        self.assertEqual(LockDoorStatus.CLOSED, lock.door_state)
        self.assertEqual(
            dateutil.parser.parse("2017-12-10T04:48:30.272Z"), lock.lock_status_datetime
        )
        self.assertEqual(
            dateutil.parser.parse("2017-12-10T04:48:30.272Z"), lock.door_state_datetime
        )

    @requests_mock.Mocker()
    def test_get_lock_detail_bridge_offline(self, mock):
        mock.register_uri(
            "get",
            API_GET_LOCK_URL.format(lock_id="ABC"),
            text=load_fixture("get_lock.offline.json"),
        )

        api = Api()
        lock = api.get_lock_detail(ACCESS_TOKEN, "ABC")

        self.assertEqual("ABC", lock.device_id)
        self.assertEqual("Test", lock.device_name)
        self.assertEqual("houseid", lock.house_id)
        self.assertEqual("ABC", lock.serial_number)
        self.assertEqual("undefined-1.59.0-1.13.2", lock.firmware_version)
        self.assertEqual(-100, lock.battery_level)
        self.assertEqual("AUG-X", lock.model)
        self.assertEqual(False, lock.bridge_is_online)
        self.assertEqual(None, lock.keypad)
        self.assertEqual(None, lock.bridge)
        self.assertEqual(False, lock.doorsense)

        self.assertEqual(LockStatus.UNKNOWN, lock.lock_status)
        self.assertEqual(LockDoorStatus.DISABLED, lock.door_state)
        self.assertEqual(None, lock.lock_status_datetime)
        self.assertEqual(None, lock.door_state_datetime)

    @requests_mock.Mocker()
    def test_get_lock_detail_doorsense_init_state(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_URL)
            .format(lock_id="A6697750D607098BAE8D6BAA11EF8063"),
            text=load_fixture("get_lock.doorsense_init.json"),
        )

        api = Api()
        lock = api.get_lock_detail(ACCESS_TOKEN, "A6697750D607098BAE8D6BAA11EF8063")

        self.assertEqual("A6697750D607098BAE8D6BAA11EF8063", lock.device_id)
        self.assertEqual("Front Door Lock", lock.device_name)
        self.assertEqual("000000000000", lock.house_id)
        self.assertEqual("X2FSW05DGA", lock.serial_number)
        self.assertEqual("109717e9-3.0.44-3.0.30", lock.firmware_version)
        self.assertEqual(88, lock.battery_level)
        self.assertEqual("Medium", lock.keypad.battery_level)
        self.assertEqual("5bc65c24e6ef2a263e1450a8", lock.keypad.device_id)
        self.assertEqual("AK-R1", lock.keypad.model)
        self.assertEqual("Front Door Lock Keypad", lock.keypad.device_name)
        self.assertIsInstance(lock.bridge, BridgeDetail)
        self.assertEqual(True, lock.bridge_is_online)
        self.assertEqual(True, lock.bridge.operative)
        self.assertEqual(False, lock.doorsense)

        self.assertEqual(LockStatus.LOCKED, lock.lock_status)
        self.assertEqual(LockDoorStatus.DISABLED, lock.door_state)
        self.assertEqual(
            dateutil.parser.parse("2017-12-10T04:48:30.272Z"), lock.lock_status_datetime
        )
        self.assertEqual(
            dateutil.parser.parse("2017-12-10T04:48:30.272Z"), lock.door_state_datetime
        )

        lock.lock_status = LockStatus.UNLOCKED
        self.assertEqual(LockStatus.UNLOCKED, lock.lock_status)

        lock.door_state = LockDoorStatus.OPEN
        self.assertEqual(LockDoorStatus.OPEN, lock.door_state)

        lock.lock_status_datetime = dateutil.parser.parse("2020-12-10T04:48:30.272Z")
        self.assertEqual(
            dateutil.parser.parse("2020-12-10T04:48:30.272Z"), lock.lock_status_datetime
        )
        lock.door_state_datetime = dateutil.parser.parse("2019-12-10T04:48:30.272Z")
        self.assertEqual(
            dateutil.parser.parse("2019-12-10T04:48:30.272Z"), lock.door_state_datetime
        )

        assert lock.get_user("cccca94e-373e-aaaa-bbbb-333396827777") == {
            "FirstName": "Foo",
            "LastName": "Bar",
            "UserType": "superuser",
            "identifiers": ["email:foo@bar.com", "phone:+177777777777"],
            "imageInfo": {
                "original": {
                    "format": "jpg",
                    "height": 949,
                    "secure_url": "https://www.image.com/foo.jpeg",
                    "url": "http://www.image.com/foo.jpeg",
                    "width": 948,
                },
                "thumbnail": {
                    "format": "jpg",
                    "height": 128,
                    "secure_url": "https://www.image.com/foo.jpeg",
                    "url": "http://www.image.com/foo.jpeg",
                    "width": 128,
                },
            },
        }

    @requests_mock.Mocker()
    def test_get_lock_status_with_locked_response(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_STATUS_URL)
            .format(lock_id=lock_id),
            text='{"status": "kAugLockState_Locked"}',
        )

        api = Api()
        status = api.get_lock_status(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockStatus.LOCKED, status)

    @requests_mock.Mocker()
    def test_get_lock_and_door_status_with_locked_response(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_STATUS_URL)
            .format(lock_id=lock_id),
            text='{"status": "kAugLockState_Locked"'
            ',"doorState": "kAugLockDoorState_Closed"}',
        )

        api = Api()
        status, door_status = api.get_lock_status(ACCESS_TOKEN, lock_id, True)

        self.assertEqual(LockStatus.LOCKED, status)
        self.assertEqual(LockDoorStatus.CLOSED, door_status)

    @requests_mock.Mocker()
    def test_get_lock_status_with_unlatched_response(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_STATUS_URL)
            .format(lock_id=lock_id),
            text='{"status": "kAugLockState_Unlatched"}',
        )

        api = Api()
        status = api.get_lock_status(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockStatus.UNLATCHED, status)

    @requests_mock.Mocker()
    def test_get_lock_status_with_unlocked_response(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_STATUS_URL)
            .format(lock_id=lock_id),
            text='{"status": "kAugLockState_Unlocked"}',
        )

        api = Api()
        status = api.get_lock_status(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockStatus.UNLOCKED, status)

    @requests_mock.Mocker()
    def test_get_lock_status_with_unknown_status_response(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_STATUS_URL)
            .format(lock_id=lock_id),
            text='{"status": "not_advertising"}',
        )

        api = Api()
        status = api.get_lock_status(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockStatus.UNKNOWN, status)

    @requests_mock.Mocker()
    def test_get_lock_door_status_with_closed_response(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_STATUS_URL)
            .format(lock_id=lock_id),
            text='{"doorState": "kAugLockDoorState_Closed"}',
        )

        api = Api()
        door_status = api.get_lock_door_status(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockDoorStatus.CLOSED, door_status)

    @requests_mock.Mocker()
    def test_get_lock_door_status_with_open_response(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_STATUS_URL)
            .format(lock_id=lock_id),
            text='{"doorState": "kAugLockDoorState_Open"}',
        )

        api = Api()
        door_status = api.get_lock_door_status(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockDoorStatus.OPEN, door_status)

    @requests_mock.Mocker()
    def test_get_lock_and_door_status_with_open_response(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_STATUS_URL)
            .format(lock_id=lock_id),
            text='{"status": "kAugLockState_Unlocked"'
            ',"doorState": "kAugLockDoorState_Open"}',
        )

        api = Api()
        door_status, status = api.get_lock_door_status(ACCESS_TOKEN, lock_id, True)

        self.assertEqual(LockDoorStatus.OPEN, door_status)
        self.assertEqual(LockStatus.UNLOCKED, status)

    @requests_mock.Mocker()
    def test_get_lock_door_status_with_unknown_response(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_LOCK_STATUS_URL)
            .format(lock_id=lock_id),
            text='{"doorState": "not_advertising"}',
        )

        api = Api()
        door_status = api.get_lock_door_status(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockDoorStatus.UNKNOWN, door_status)

    @requests_mock.Mocker()
    def test_lock_from_fixture(self, mock):
        lock_id = 1234
        mock.register_uri(
            "put",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_LOCK_URL)
            .format(lock_id=lock_id),
            text=load_fixture("lock.json"),
        )

        api = Api()
        status = api.lock(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockStatus.LOCKED, status)

    @requests_mock.Mocker()
    def test_unlock_from_fixture(self, mock):
        lock_id = 1234
        mock.register_uri(
            "put",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_UNLOCK_URL)
            .format(lock_id=lock_id),
            text=load_fixture("unlock.json"),
        )

        api = Api()
        status = api.unlock(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockStatus.UNLOCKED, status)

    @requests_mock.Mocker()
    def test_lock_return_activities_from_fixture(self, mock):
        lock_id = 1234
        mock.register_uri(
            "put",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_LOCK_URL)
            .format(lock_id=lock_id),
            text=load_fixture("lock.json"),
        )

        api = Api()
        activities = api.lock_return_activities(ACCESS_TOKEN, lock_id)
        expected_lock_dt = (
            dateutil.parser.parse("2020-02-19T19:44:54.371Z")
            .astimezone(tz=tzlocal())
            .replace(tzinfo=None)
        )

        self.assertEqual(len(activities), 2)
        self.assertIsInstance(activities[0], yalexs.activity.LockOperationActivity)
        self.assertEqual(activities[0].device_id, "ABC123")
        self.assertEqual(activities[0].device_type, "lock")
        self.assertEqual(activities[0].action, "lock")
        self.assertEqual(activities[0].activity_start_time, expected_lock_dt)
        self.assertEqual(activities[0].activity_end_time, expected_lock_dt)
        self.assertIsInstance(activities[1], yalexs.activity.DoorOperationActivity)
        self.assertEqual(activities[1].device_id, "ABC123")
        self.assertEqual(activities[1].device_type, "lock")
        self.assertEqual(activities[1].action, "doorclosed")
        self.assertEqual(activities[0].activity_start_time, expected_lock_dt)
        self.assertEqual(activities[0].activity_end_time, expected_lock_dt)

    @requests_mock.Mocker()
    def test_unlock_return_activities_from_fixture(self, mock):
        lock_id = 1234
        mock.register_uri(
            "put",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_UNLOCK_URL)
            .format(lock_id=lock_id),
            text=load_fixture("unlock.json"),
        )

        api = Api()
        activities = api.unlock_return_activities(ACCESS_TOKEN, lock_id)
        expected_unlock_dt = (
            dateutil.parser.parse("2020-02-19T19:44:26.745Z")
            .astimezone(tz=tzlocal())
            .replace(tzinfo=None)
        )

        self.assertEqual(len(activities), 2)
        self.assertIsInstance(activities[0], yalexs.activity.LockOperationActivity)
        self.assertEqual(activities[0].device_id, "ABC")
        self.assertEqual(activities[0].device_type, "lock")
        self.assertEqual(activities[0].action, "unlock")
        self.assertEqual(activities[0].activity_start_time, expected_unlock_dt)
        self.assertEqual(activities[0].activity_end_time, expected_unlock_dt)
        self.assertIsInstance(activities[1], yalexs.activity.DoorOperationActivity)
        self.assertEqual(activities[1].device_id, "ABC")
        self.assertEqual(activities[1].device_type, "lock")
        self.assertEqual(activities[1].action, "doorclosed")
        self.assertEqual(activities[1].activity_start_time, expected_unlock_dt)
        self.assertEqual(activities[1].activity_end_time, expected_unlock_dt)

    @requests_mock.Mocker()
    def test_lock_return_activities_from_fixture_with_no_doorstate(self, mock):
        lock_id = 1234
        mock.register_uri(
            "put",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_LOCK_URL)
            .format(lock_id=lock_id),
            text=load_fixture("lock_without_doorstate.json"),
        )

        api = Api()
        activities = api.lock_return_activities(ACCESS_TOKEN, lock_id)
        expected_lock_dt = (
            dateutil.parser.parse("2020-02-19T19:44:54.371Z")
            .astimezone(tz=tzlocal())
            .replace(tzinfo=None)
        )

        self.assertEqual(len(activities), 1)
        self.assertIsInstance(activities[0], yalexs.activity.LockOperationActivity)
        self.assertEqual(activities[0].device_id, "ABC123")
        self.assertEqual(activities[0].device_type, "lock")
        self.assertEqual(activities[0].action, "lock")
        self.assertEqual(activities[0].activity_start_time, expected_lock_dt)
        self.assertEqual(activities[0].activity_end_time, expected_lock_dt)

    @requests_mock.Mocker()
    def test_unlock_return_activities_from_fixture_with_no_doorstate(self, mock):
        lock_id = 1234
        mock.register_uri(
            "put",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_UNLOCK_URL)
            .format(lock_id=lock_id),
            text=load_fixture("unlock_without_doorstate.json"),
        )

        api = Api()
        activities = api.unlock_return_activities(ACCESS_TOKEN, lock_id)
        expected_unlock_dt = (
            dateutil.parser.parse("2020-02-19T19:44:26.745Z")
            .astimezone(tz=tzlocal())
            .replace(tzinfo=None)
        )

        self.assertEqual(len(activities), 1)
        self.assertIsInstance(activities[0], yalexs.activity.LockOperationActivity)
        self.assertEqual(activities[0].device_id, "ABC123")
        self.assertEqual(activities[0].device_type, "lock")
        self.assertEqual(activities[0].action, "unlock")
        self.assertEqual(activities[0].activity_start_time, expected_unlock_dt)
        self.assertEqual(activities[0].activity_end_time, expected_unlock_dt)

    @requests_mock.Mocker()
    def test_lock(self, mock):
        lock_id = 1234
        mock.register_uri(
            "put",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_LOCK_URL)
            .format(lock_id=lock_id),
            text='{"status":"locked",'
            '"dateTime":"2017-12-10T07:43:39.056Z",'
            '"isLockStatusChanged":false,'
            '"valid":true}',
        )

        api = Api()
        status = api.lock(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockStatus.LOCKED, status)

    @requests_mock.Mocker()
    def test_unlatch(self, mock):
        lock_id = 1234
        mock.register_uri(
            "put",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_UNLATCH_URL)
            .format(lock_id=lock_id),
            text='{"status": "unlatched"}',
        )

        api = Api()
        status = api.unlatch(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockStatus.UNLATCHED, status)

    @requests_mock.Mocker()
    def test_unlock(self, mock):
        lock_id = 1234
        mock.register_uri(
            "put",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_UNLOCK_URL)
            .format(lock_id=lock_id),
            text='{"status": "unlocked"}',
        )

        api = Api()
        status = api.unlock(ACCESS_TOKEN, lock_id)

        self.assertEqual(LockStatus.UNLOCKED, status)

    @requests_mock.Mocker()
    def test_get_pins(self, mock):
        lock_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_PINS_URL)
            .format(lock_id=lock_id),
            text=load_fixture("get_pins.json"),
        )

        api = Api()
        pins = api.get_pins(ACCESS_TOKEN, lock_id)

        self.assertEqual(1, len(pins))

        first = pins[0]
        self.assertEqual("epoZ87XSPqxlFdsaYyJiRRVR", first.pin_id)
        self.assertEqual("A6697750D607098BAE8D6BAA11EF8063", first.lock_id)
        self.assertEqual("c3b3a94f-473z-61a3-a8d1-a6e99482787a", first.user_id)
        self.assertEqual("in-use", first.state)
        self.assertEqual("123456", first.pin)
        self.assertEqual(646545456465161, first.slot)
        self.assertEqual("one-time", first.access_type)
        self.assertEqual("John", first.first_name)
        self.assertEqual("Doe", first.last_name)
        self.assertEqual(True, first.unverified)
        self.assertEqual(utc_of(2016, 11, 26, 22, 27, 11, 176000), first.created_at)
        self.assertEqual(utc_of(2017, 11, 23, 00, 42, 19, 470000), first.updated_at)
        self.assertEqual(utc_of(2017, 12, 10, 3, 12, 55, 563000), first.loaded_date)
        self.assertEqual(utc_of(2018, 1, 1, 1, 1, 1, 563000), first.access_start_time)
        self.assertEqual(utc_of(2018, 12, 1, 1, 1, 1, 563000), first.access_end_time)
        self.assertEqual(utc_of(2018, 11, 5, 10, 2, 41, 684000), first.access_times)

    @requests_mock.Mocker()
    def test_get_house_activities(self, mock):
        house_id = 1234
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND)
            .get_brand_url(API_GET_HOUSE_ACTIVITIES_URL)
            .format(house_id=house_id),
            text=load_fixture("get_house_activities.json"),
        )

        api = Api()
        activities = api.get_house_activities(ACCESS_TOKEN, house_id)

        self.assertEqual(10, len(activities))

        self.assertIsInstance(activities[0], yalexs.activity.LockOperationActivity)
        self.assertIsInstance(activities[1], yalexs.activity.LockOperationActivity)
        self.assertIsInstance(activities[2], yalexs.activity.LockOperationActivity)
        self.assertIsInstance(activities[3], yalexs.activity.LockOperationActivity)
        self.assertIsInstance(activities[4], yalexs.activity.LockOperationActivity)
        self.assertIsInstance(activities[5], yalexs.activity.DoorOperationActivity)
        self.assertIsInstance(activities[6], yalexs.activity.DoorOperationActivity)
        self.assertIsInstance(activities[7], yalexs.activity.DoorOperationActivity)
        self.assertIsInstance(activities[8], yalexs.activity.LockOperationActivity)
        self.assertIsInstance(activities[9], yalexs.activity.LockOperationActivity)

    def test__raise_response_exceptions(self):
        four_two_eight = MockedResponse(content="not json")
        four_two_eight.status_code = 404
        four_two_eight.url = "http://code404.tld"

        try:
            _raise_response_exceptions(four_two_eight)
        except Exception as err:
            self.assertIsInstance(err, HTTPError)
            self.assertNotIsInstance(err, AugustApiHTTPError)

        four_two_eight = MockedResponse(
            content='{"code":97,"message":"four two eight"}'
        )
        four_two_eight.status_code = 428
        four_two_eight.url = "http://code428.tld"
        four_two_eight.headers = CaseInsensitiveDict(
            {"Content-Type": "application/json"}
        )

        try:
            _raise_response_exceptions(four_two_eight)
        except AugustApiHTTPError as err:
            self.assertEqual(str(err), "The operation failed because: four two eight")

        ERROR_MAP = {
            422: "The operation failed because the bridge (connect) is offline.",
            423: "The operation failed because the bridge (connect) is in use.",
            408: "The operation timed out because the bridge (connect) failed to respond.",
        }

        for status_code in ERROR_MAP:
            mocked_response = MockedResponse(content="ignored")
            mocked_response.status_code = status_code
            mocked_response.url = "http://code"

            try:
                _raise_response_exceptions(mocked_response)
            except AugustApiHTTPError as err:
                self.assertEqual(str(err), ERROR_MAP[status_code])

    @requests_mock.Mocker()
    def test_get_user(self, mock):
        mock.register_uri(
            "get",
            ApiCommon(DEFAULT_BRAND).get_brand_url(API_GET_USER_URL),
            text='{"UserID": "abc"}',
        )

        user_details = Api().get_user(ACCESS_TOKEN)

        self.assertEqual(user_details, {"UserID": "abc"})


class MockedResponse(Response):
    def __init__(self, *args, **kwargs):
        content = kwargs.pop("content", None)
        super().__init__(*args, **kwargs)
        self._mocked_content = content

    @property
    def content(self):
        return self._mocked_content
