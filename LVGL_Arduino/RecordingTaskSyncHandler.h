#ifndef RECORDING_TASK_SYNC_HANDLER_H
#define RECORDING_TASK_SYNC_HANDLER_H

#ifdef __cplusplus
extern "C" {
#endif

// Exposed to C files like ui.c
void RestartDynamicRecordingTask(void);

#ifdef __cplusplus
}
#endif

#ifdef __cplusplus

#include <vector>

// Sampling level structure
struct SamplingSlot {
    int fromMinutes;
    int toMinutes;
    int intervalMinutes;
};

// Load the schedule from SD card
void loadSamplingSchedule();

// Start the task (used internally or if needed from C++)
void StartDynamicRecordingTask();

#endif  // __cplusplus

#endif  // RECORDING_TASK_SYNC_HANDLER_H
