// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from rov_interfaces:msg/ThrusterPower.idl
// generated code does not contain a copyright notice
#include "rov_interfaces/msg/detail/thruster_power__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


bool
rov_interfaces__msg__ThrusterPower__init(rov_interfaces__msg__ThrusterPower * msg)
{
  if (!msg) {
    return false;
  }
  // power_values
  return true;
}

void
rov_interfaces__msg__ThrusterPower__fini(rov_interfaces__msg__ThrusterPower * msg)
{
  if (!msg) {
    return;
  }
  // power_values
}

bool
rov_interfaces__msg__ThrusterPower__are_equal(const rov_interfaces__msg__ThrusterPower * lhs, const rov_interfaces__msg__ThrusterPower * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // power_values
  for (size_t i = 0; i < 6; ++i) {
    if (lhs->power_values[i] != rhs->power_values[i]) {
      return false;
    }
  }
  return true;
}

bool
rov_interfaces__msg__ThrusterPower__copy(
  const rov_interfaces__msg__ThrusterPower * input,
  rov_interfaces__msg__ThrusterPower * output)
{
  if (!input || !output) {
    return false;
  }
  // power_values
  for (size_t i = 0; i < 6; ++i) {
    output->power_values[i] = input->power_values[i];
  }
  return true;
}

rov_interfaces__msg__ThrusterPower *
rov_interfaces__msg__ThrusterPower__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  rov_interfaces__msg__ThrusterPower * msg = (rov_interfaces__msg__ThrusterPower *)allocator.allocate(sizeof(rov_interfaces__msg__ThrusterPower), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(rov_interfaces__msg__ThrusterPower));
  bool success = rov_interfaces__msg__ThrusterPower__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
rov_interfaces__msg__ThrusterPower__destroy(rov_interfaces__msg__ThrusterPower * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    rov_interfaces__msg__ThrusterPower__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
rov_interfaces__msg__ThrusterPower__Sequence__init(rov_interfaces__msg__ThrusterPower__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  rov_interfaces__msg__ThrusterPower * data = NULL;

  if (size) {
    data = (rov_interfaces__msg__ThrusterPower *)allocator.zero_allocate(size, sizeof(rov_interfaces__msg__ThrusterPower), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = rov_interfaces__msg__ThrusterPower__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        rov_interfaces__msg__ThrusterPower__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
rov_interfaces__msg__ThrusterPower__Sequence__fini(rov_interfaces__msg__ThrusterPower__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      rov_interfaces__msg__ThrusterPower__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

rov_interfaces__msg__ThrusterPower__Sequence *
rov_interfaces__msg__ThrusterPower__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  rov_interfaces__msg__ThrusterPower__Sequence * array = (rov_interfaces__msg__ThrusterPower__Sequence *)allocator.allocate(sizeof(rov_interfaces__msg__ThrusterPower__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = rov_interfaces__msg__ThrusterPower__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
rov_interfaces__msg__ThrusterPower__Sequence__destroy(rov_interfaces__msg__ThrusterPower__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    rov_interfaces__msg__ThrusterPower__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
rov_interfaces__msg__ThrusterPower__Sequence__are_equal(const rov_interfaces__msg__ThrusterPower__Sequence * lhs, const rov_interfaces__msg__ThrusterPower__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!rov_interfaces__msg__ThrusterPower__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
rov_interfaces__msg__ThrusterPower__Sequence__copy(
  const rov_interfaces__msg__ThrusterPower__Sequence * input,
  rov_interfaces__msg__ThrusterPower__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(rov_interfaces__msg__ThrusterPower);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    rov_interfaces__msg__ThrusterPower * data =
      (rov_interfaces__msg__ThrusterPower *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!rov_interfaces__msg__ThrusterPower__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          rov_interfaces__msg__ThrusterPower__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!rov_interfaces__msg__ThrusterPower__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
