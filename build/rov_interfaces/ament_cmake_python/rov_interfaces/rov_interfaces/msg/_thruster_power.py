# generated from rosidl_generator_py/resource/_idl.py.em
# with input from rov_interfaces:msg/ThrusterPower.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

# Member 'power_values'
import numpy  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_ThrusterPower(type):
    """Metaclass of message 'ThrusterPower'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('rov_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'rov_interfaces.msg.ThrusterPower')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__thruster_power
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__thruster_power
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__thruster_power
            cls._TYPE_SUPPORT = module.type_support_msg__msg__thruster_power
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__thruster_power

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class ThrusterPower(metaclass=Metaclass_ThrusterPower):
    """Message class 'ThrusterPower'."""

    __slots__ = [
        '_power_values',
    ]

    _fields_and_field_types = {
        'power_values': 'float[6]',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.Array(rosidl_parser.definition.BasicType('float'), 6),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        if 'power_values' not in kwargs:
            self.power_values = numpy.zeros(6, dtype=numpy.float32)
        else:
            self.power_values = numpy.array(kwargs.get('power_values'), dtype=numpy.float32)
            assert self.power_values.shape == (6, )

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if any(self.power_values != other.power_values):
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def power_values(self):
        """Message field 'power_values'."""
        return self._power_values

    @power_values.setter
    def power_values(self, value):
        if isinstance(value, numpy.ndarray):
            assert value.dtype == numpy.float32, \
                "The 'power_values' numpy.ndarray() must have the dtype of 'numpy.float32'"
            assert value.size == 6, \
                "The 'power_values' numpy.ndarray() must have a size of 6"
            self._power_values = value
            return
        if __debug__:
            from collections.abc import Sequence
            from collections.abc import Set
            from collections import UserList
            from collections import UserString
            assert \
                ((isinstance(value, Sequence) or
                  isinstance(value, Set) or
                  isinstance(value, UserList)) and
                 not isinstance(value, str) and
                 not isinstance(value, UserString) and
                 len(value) == 6 and
                 all(isinstance(v, float) for v in value) and
                 all(not (val < -3.402823466e+38 or val > 3.402823466e+38) or math.isinf(val) for val in value)), \
                "The 'power_values' field must be a set or sequence with length 6 and each value of type 'float' and each float in [-340282346600000016151267322115014000640.000000, 340282346600000016151267322115014000640.000000]"
        self._power_values = numpy.array(value, dtype=numpy.float32)
