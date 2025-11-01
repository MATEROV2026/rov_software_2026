// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from rov_interfaces:msg/ThrusterPower.idl
// generated code does not contain a copyright notice

#ifndef ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__TRAITS_HPP_
#define ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "rov_interfaces/msg/detail/thruster_power__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace rov_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const ThrusterPower & msg,
  std::ostream & out)
{
  out << "{";
  // member: power_values
  {
    if (msg.power_values.size() == 0) {
      out << "power_values: []";
    } else {
      out << "power_values: [";
      size_t pending_items = msg.power_values.size();
      for (auto item : msg.power_values) {
        rosidl_generator_traits::value_to_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const ThrusterPower & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: power_values
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.power_values.size() == 0) {
      out << "power_values: []\n";
    } else {
      out << "power_values:\n";
      for (auto item : msg.power_values) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "- ";
        rosidl_generator_traits::value_to_yaml(item, out);
        out << "\n";
      }
    }
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const ThrusterPower & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace rov_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use rov_interfaces::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const rov_interfaces::msg::ThrusterPower & msg,
  std::ostream & out, size_t indentation = 0)
{
  rov_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use rov_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const rov_interfaces::msg::ThrusterPower & msg)
{
  return rov_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<rov_interfaces::msg::ThrusterPower>()
{
  return "rov_interfaces::msg::ThrusterPower";
}

template<>
inline const char * name<rov_interfaces::msg::ThrusterPower>()
{
  return "rov_interfaces/msg/ThrusterPower";
}

template<>
struct has_fixed_size<rov_interfaces::msg::ThrusterPower>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<rov_interfaces::msg::ThrusterPower>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<rov_interfaces::msg::ThrusterPower>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__TRAITS_HPP_
