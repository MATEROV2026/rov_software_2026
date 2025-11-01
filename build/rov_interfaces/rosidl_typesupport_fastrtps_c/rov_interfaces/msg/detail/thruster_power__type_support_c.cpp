// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from rov_interfaces:msg/ThrusterPower.idl
// generated code does not contain a copyright notice
#include "rov_interfaces/msg/detail/thruster_power__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "rov_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "rov_interfaces/msg/detail/thruster_power__struct.h"
#include "rov_interfaces/msg/detail/thruster_power__functions.h"
#include "fastcdr/Cdr.h"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

// includes and forward declarations of message dependencies and their conversion functions

#if defined(__cplusplus)
extern "C"
{
#endif


// forward declare type support functions


using _ThrusterPower__ros_msg_type = rov_interfaces__msg__ThrusterPower;

static bool _ThrusterPower__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _ThrusterPower__ros_msg_type * ros_message = static_cast<const _ThrusterPower__ros_msg_type *>(untyped_ros_message);
  // Field name: power_values
  {
    size_t size = 6;
    auto array_ptr = ros_message->power_values;
    cdr.serializeArray(array_ptr, size);
  }

  return true;
}

static bool _ThrusterPower__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _ThrusterPower__ros_msg_type * ros_message = static_cast<_ThrusterPower__ros_msg_type *>(untyped_ros_message);
  // Field name: power_values
  {
    size_t size = 6;
    auto array_ptr = ros_message->power_values;
    cdr.deserializeArray(array_ptr, size);
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_rov_interfaces
size_t get_serialized_size_rov_interfaces__msg__ThrusterPower(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _ThrusterPower__ros_msg_type * ros_message = static_cast<const _ThrusterPower__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name power_values
  {
    size_t array_size = 6;
    auto array_ptr = ros_message->power_values;
    (void)array_ptr;
    size_t item_size = sizeof(array_ptr[0]);
    current_alignment += array_size * item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

static uint32_t _ThrusterPower__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_rov_interfaces__msg__ThrusterPower(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_rov_interfaces
size_t max_serialized_size_rov_interfaces__msg__ThrusterPower(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;

  // member: power_values
  {
    size_t array_size = 6;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = rov_interfaces__msg__ThrusterPower;
    is_plain =
      (
      offsetof(DataType, power_values) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _ThrusterPower__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_rov_interfaces__msg__ThrusterPower(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_ThrusterPower = {
  "rov_interfaces::msg",
  "ThrusterPower",
  _ThrusterPower__cdr_serialize,
  _ThrusterPower__cdr_deserialize,
  _ThrusterPower__get_serialized_size,
  _ThrusterPower__max_serialized_size
};

static rosidl_message_type_support_t _ThrusterPower__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_ThrusterPower,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, rov_interfaces, msg, ThrusterPower)() {
  return &_ThrusterPower__type_support;
}

#if defined(__cplusplus)
}
#endif
