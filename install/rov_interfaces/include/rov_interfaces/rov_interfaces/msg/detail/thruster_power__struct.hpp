// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from rov_interfaces:msg/ThrusterPower.idl
// generated code does not contain a copyright notice

#ifndef ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__STRUCT_HPP_
#define ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__rov_interfaces__msg__ThrusterPower __attribute__((deprecated))
#else
# define DEPRECATED__rov_interfaces__msg__ThrusterPower __declspec(deprecated)
#endif

namespace rov_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct ThrusterPower_
{
  using Type = ThrusterPower_<ContainerAllocator>;

  explicit ThrusterPower_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      std::fill<typename std::array<float, 6>::iterator, float>(this->power_values.begin(), this->power_values.end(), 0.0f);
    }
  }

  explicit ThrusterPower_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : power_values(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      std::fill<typename std::array<float, 6>::iterator, float>(this->power_values.begin(), this->power_values.end(), 0.0f);
    }
  }

  // field types and members
  using _power_values_type =
    std::array<float, 6>;
  _power_values_type power_values;

  // setters for named parameter idiom
  Type & set__power_values(
    const std::array<float, 6> & _arg)
  {
    this->power_values = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    rov_interfaces::msg::ThrusterPower_<ContainerAllocator> *;
  using ConstRawPtr =
    const rov_interfaces::msg::ThrusterPower_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<rov_interfaces::msg::ThrusterPower_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<rov_interfaces::msg::ThrusterPower_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      rov_interfaces::msg::ThrusterPower_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<rov_interfaces::msg::ThrusterPower_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      rov_interfaces::msg::ThrusterPower_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<rov_interfaces::msg::ThrusterPower_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<rov_interfaces::msg::ThrusterPower_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<rov_interfaces::msg::ThrusterPower_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__rov_interfaces__msg__ThrusterPower
    std::shared_ptr<rov_interfaces::msg::ThrusterPower_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__rov_interfaces__msg__ThrusterPower
    std::shared_ptr<rov_interfaces::msg::ThrusterPower_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const ThrusterPower_ & other) const
  {
    if (this->power_values != other.power_values) {
      return false;
    }
    return true;
  }
  bool operator!=(const ThrusterPower_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct ThrusterPower_

// alias to use template instance with default allocator
using ThrusterPower =
  rov_interfaces::msg::ThrusterPower_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace rov_interfaces

#endif  // ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__STRUCT_HPP_
