from enum import Enum

class EmailType(str, Enum):
    TRAVEL_CODE = "Mã truy cập Netflix tạm thời của bạn"
    UPDATE_FAMILY = "Cách cập nhật Hộ gia đình Netflix"