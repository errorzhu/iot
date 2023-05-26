FIELD_TYPE_INT = 0
FIELD_TYPE_STR = 1


class Field(object):
    def __init__(self, tag, length):
        self._tag = tag
        self._length = length
        self._data = None

    def _read_n_bits(self, b: bytes, s: int, e: int) -> int:
        """
        获取字节串 b 中从第 s 位到第 e 位的值，s 和 e 从右往左数，从0开始计数。
        """
        if s > e:
            raise ValueError("起始位置 s 不能大于结束位置 e")
        byte_start = s // 8  # 计算要获取的起始字节的下标
        byte_end = e // 8  # 计算要获取的结束字节的下标
        bit_start = s % 8  # 计算要获取的起始位在字节中的下标
        bit_end = e % 8  # 计算要获取的结束位在字节中的下标
        result = 0  # 初始化结果为0
        for i in range(byte_start, byte_end + 1):
            byte_value = b[i]  # 获取字节的值
            if i == byte_start:
                byte_value &= 0xFF >> bit_start  # 如果是起始字节，需要掩码处理
            if i == byte_end:
                byte_value &= 0xFF << (7 - bit_end)  # 如果是结束字节，需要掩码处理
            result <<= 8  # 将结果左移8位
            result |= byte_value  # 将字节的值拼接到结果中
        result >>= 7 - bit_end  # 将结果右移，将结束位置的位数移到最右边
        # result &= (0xff >> (7 - bit_end + bit_start))  # 对结果进行掩码处理，去掉多余的位
        return result

    def decode(self, data, index):
        self._data = self._read_n_bits(data, index, index + self._length - 1)

    @property
    def tag(self):
        return self._tag

    @property
    def data(self):
        return self._data

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        self._length = length


class FixField(Field):
    def __init__(self, tag, length, type=None):
        self._length = length
        self._type = type
        self._tag = tag


class VariableField(Field):
    def __init__(self, tag, variables, type=None):
        self._length = 0
        self._type = type
        self._tag = tag
        self._variables = variables

    def decode(self, data, index):
        if "length" in self._variables:
            self._length = self._variables["length"]()
        super().decode(data, index)


class CombineField(Field):
    def __init__(self, *fields, **kwargs):
        self._tag = kwargs.get("tag")
        self._fields = [field for field in fields]
        self._data = {}
        self._length = 0

    def decode(self, data, index):
        self._length = 0
        for field in self._fields:
            field.decode(data, index)
            self._data[field.tag] = {"data": field.data, "length": field.length}
            self._length += field.length


class RepeatField(Field):
    def __init__(self, tag, field, n):
        self._tag = tag
        self._fields = [field for i in range(n)]
        self._data = []
        self._length = 0

    def decode(self, data, index):
        for field in self._fields:
            field.decode(data, index)
            self._data.append({"data": field.data, "length": field.length})
            self._length += field.length


class Frame(object):
    def __init__(self, *fields):
        self._fields = []
        self._fields_map = {}
        self._index = 0
        for field in fields:
            self._add_field(field)

    def _add_field(self, field):
        self._fields.append(field)
        self._fields_map[field.tag] = field

    def decode(self, data):
        for field in self._fields:
            field.decode(data, self._index)
            self._index += field.length
        self._index = 0

    def to_json(self):
        result = {}
        for field in self._fields:
            result[field.tag] = {"data": field.data, "length": field.length}
        return result

    def get(self, field):
        return self._fields_map.get(field)


if __name__ == "__main__":
    header = FixField(tag="帧头", type=FIELD_TYPE_STR, length=8)
    address = FixField(tag="地址域", type=FIELD_TYPE_INT, length=48)
    direction = FixField(tag="方向", length=1)
    answer_flag = FixField(tag="应答标志", length=1)
    follow_frame_flag = FixField(tag="后续帧标志", length=1)
    function_code = FixField(tag="功能码", length=5)
    L = FixField(tag="数据域长度", length=8)
    di3 = FixField(tag="数据标识结构3", length=8)
    di2 = FixField(tag="数据标识结构2", length=8)
    di1 = FixField(tag="数据标识结构1", length=8)
    di0 = FixField(tag="数据标识结构0", length=8)
    v = VariableField(tag="动态结构", variables={"length": lambda: L.data * 8})
    c1 = FixField(tag="子结构1", length=8)
    c2 = FixField(tag="子结构2", length=8)
    c = CombineField(c1, c2, tag="组合结构")
    r = RepeatField(tag="重复结构", field=c, n=3)
    frame = Frame(
        header,
        address,
        direction,
        answer_flag,
        follow_frame_flag,
        function_code,
        L,
        di3,
        di2,
        di1,
        di0,
        v,
        r,
    )
    frame.decode(
        bytes(
            [
                0x68,
                0x99,
                0x99,
                0x99,
                0x99,
                0x99,
                0x99,
                0b00011001,
                0x01,
                0x00,
                0x01,
                0x00,
                0x00,
                0x91,
                0x01,
                0x02,
                0x01,
                0x02,
                0x01,
                0x02,
            ]
        )
    )
    print(frame.to_json())
    print(frame.get("帧头").data)
