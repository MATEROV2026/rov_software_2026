// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from rov_interfaces:msg/ThrusterPower.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "rov_interfaces/msg/detail/thruster_power__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace rov_interfaces
{

namespace msg
{

namespace rosidl_typesupport_introspection_cpp
{

void ThrusterPower_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) rov_interfaces::msg::ThrusterPower(_init);
}

void ThrusterPower_fini_function(void * message_memory)
{
  auto typed_message = static_cast<rov_interfaces::msg::ThrusterPower *>(message_memory);
  typed_message->~ThrusterPower();
}

size_t size_function__ThrusterPower__power_values(const void * untyped_member)
{
  (void)untyped_member;
  return 6;
}

const void * get_const_function__ThrusterPower__power_values(const void * untyped_member, size_t index)
{
  const auto & member =
    *reinterpret_cast<const std::array<float, 6> *>(untyped_member);
  return &member[index];
}

void * get_function__ThrusterPower__power_values(void * untyped_member, size_t index)
{
  auto & member =
    *reinterpret_cast<std::array<float, 6> *>(untyped_member);
  return &member[index];
}

void fetch_function__ThrusterPower__power_values(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const auto & item = *reinterpret_cast<const float *>(
    get_const_function__ThrusterPower__power_values(untyped_member, index));
  auto & value = *reinterpret_cast<float *>(untyped_value);
  value = item;
}

void assign_function__ThrusterPower__power_values(
  void * untyped_member, size_t index, const void * untyped_value)
{
  auto & item = *reinterpret_cast<float *>(
    get_function__ThrusterPower__power_values(untyped_member, index));
  const auto & value = *reinterpret_cast<const float *>(untyped_value);
  item = value;
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember ThrusterPower_message_member_array[1] = {
  {
    "power_values",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    true,  // is array
    6,  // array size
    false,  // is upper bound
    offsetof(rov_interfaces::msg::ThrusterPower, power_values),  // bytes offset in struct
    nullptr,  // default value
    size_function__ThrusterPower__power_values,  // size() function pointer
    get_const_function__ThrusterPower__power_values,  // get_const(index) function pointer
    get_function__ThrusterPower__power_values,  // get(index) function pointer
    fetch_function__ThrusterPower__power_values,  // fetch(index, &value) function pointer
    assign_function__ThrusterPower__power_values,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers ThrusterPower_message_members = {
  "rov_interfaces::msg",  // message namespace
  "ThrusterPower",  // message name
  1,  // number of fields
  sizeof(rov_interfaces::msg::ThrusterPower),
  ThrusterPower_message_member_array,  // message members
  ThrusterPower_init_function,  // function to initialize message memory (memory has to be allocated)
  ThrusterPower_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t ThrusterPower_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &ThrusterPower_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace msg

}  // namespace rov_interfaces


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<rov_interfaces::msg::ThrusterPower>()
{
  return &::rov_interfaces::msg::rosidl_typesupport_introspection_cpp::ThrusterPower_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, rov_interfaces, msg, ThrusterPower)() {
  return &::rov_interfaces::msg::rosidl_typesupport_introspection_cpp::ThrusterPower_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
