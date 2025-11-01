// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from rov_interfaces:msg/ThrusterPower.idl
// generated code does not contain a copyright notice

#ifndef ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__STRUCT_H_
#define ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in msg/ThrusterPower in the package rov_interfaces.
/**
  * A message to hold power values for 6 thrusters
  * Values can be from -1.0 (full reverse) to 1.0 (full forward)
 */
typedef struct rov_interfaces__msg__ThrusterPower
{
  float power_values[6];
} rov_interfaces__msg__ThrusterPower;

// Struct for a sequence of rov_interfaces__msg__ThrusterPower.
typedef struct rov_interfaces__msg__ThrusterPower__Sequence
{
  rov_interfaces__msg__ThrusterPower * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} rov_interfaces__msg__ThrusterPower__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // ROV_INTERFACES__MSG__DETAIL__THRUSTER_POWER__STRUCT_H_
