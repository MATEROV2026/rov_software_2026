// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from rov_interfaces:msg/ThrusterPower.idl
// generated code does not contain a copyright notice

#ifndef ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__BUILDER_HPP_
#define ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "rov_interfaces/msg/detail/thruster_power__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace rov_interfaces
{

namespace msg
{

namespace builder
{

class Init_ThrusterPower_power_values
{
public:
  Init_ThrusterPower_power_values()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::rov_interfaces::msg::ThrusterPower power_values(::rov_interfaces::msg::ThrusterPower::_power_values_type arg)
  {
    msg_.power_values = std::move(arg);
    return std::move(msg_);
  }

private:
  ::rov_interfaces::msg::ThrusterPower msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::rov_interfaces::msg::ThrusterPower>()
{
  return rov_interfaces::msg::builder::Init_ThrusterPower_power_values();
}

}  // namespace rov_interfaces

#endif  // ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__BUILDER_HPP_
