// SPDX-FileCopyrightText: 2018 me-no-dev for Espressif Systems
//
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// Modified by Brent Rubell for Adafruit Industries

// RA Filtering
typedef struct {
  size_t size;  // number of values used for filtering
  size_t index; // current value index
  size_t count; // value count
  int sum;
  int *values; // array to be filled with values
} ra_filter_t;

static ra_filter_t ra_filter;

static ra_filter_t *ra_filter_init(ra_filter_t *filter, size_t sample_size) {
  memset(filter, 0, sizeof(ra_filter_t));

  filter->values = (int *)malloc(sample_size * sizeof(int));
  if (!filter->values) {
    return NULL;
  }
  memset(filter->values, 0, sample_size * sizeof(int));

  filter->size = sample_size;
  return filter;
}

static int ra_filter_run(ra_filter_t *filter, int value) {
  if (!filter->values) {
    return value;
  }
  filter->sum -= filter->values[filter->index];
  filter->values[filter->index] = value;
  filter->sum += filter->values[filter->index];
  filter->index++;
  filter->index = filter->index % filter->size;
  if (filter->count < filter->size) {
    filter->count++;
  }
  return filter->sum / filter->count;
}