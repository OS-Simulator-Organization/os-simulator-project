# Shared Data Model

## Overview

This document describes the shared data model used by the operating
system simulation. The model is implemented with Python `dataclasses`,
type annotations, and enumerations. It provides common entities for
process management, memory management, file-system management, security,
device management, and network management.

## System States and Enumerations

### `ProcessState`

Represents the lifecycle state of a process.

  -----------------------------------------------------------------------
  Value                               Description
  ----------------------------------- -----------------------------------
  `NEW`                               Process has been created but has
                                      not yet entered the ready queue.

  `READY`                             Process is ready to execute and is
                                      waiting for CPU time.

  `RUNNING`                           Process is currently executing on
                                      the CPU.

  `WAITING`                           Process is waiting for an event,
                                      such as I/O, a page fault, or a
                                      network packet.

  `TERMINATED`                        Process has completed or has
                                      otherwise been terminated.
  -----------------------------------------------------------------------

### `DeviceType`

Identifies a category of device managed by the system.

  -----------------------------------------------------------------------
  Value                               Description
  ----------------------------------- -----------------------------------
  `DISK`                              Storage device; comments indicate
                                      SSTF or SCAN scheduling may be
                                      used.

  `PRINTER`                           Output device; comments indicate
                                      FCFS scheduling may be used.

  `KEYBOARD`                          Input device; comments indicate
                                      FCFS scheduling may be used.
  -----------------------------------------------------------------------

## Entity Models

## 1. Process Manager

### `Process`

Represents a process scheduled or managed by the operating system.

  -----------------------------------------------------------------------------
  Attribute            Type              Default              Description
  -------------------- ----------------- -------------------- -----------------
  `pid`                `str`             Required             Unique process
                                                              identifier.

  `owner_id`           `str`             Required             Identifier of the
                                                              user who owns the
                                                              process.

  `arrival_time`       `int`             Required             Time at which the
                                                              process arrives
                                                              in the system or
                                                              scheduling queue.

  `burst_time`         `int`             Required             Total CPU
                                                              execution time
                                                              required by the
                                                              process.

  `priority`           `int`             Required             Scheduling
                                                              priority value.
                                                              The exact
                                                              priority
                                                              convention is
                                                              defined by the
                                                              scheduler.

  `remaining_time`     `int`             Required             CPU execution
                                                              time remaining;
                                                              used by
                                                              algorithms such
                                                              as SRTF and
                                                              Round-Robin.

  `state`              `ProcessState`    `ProcessState.NEW`   Current process
                                                              lifecycle state.

  `allocated_frames`   `List[int]`       Empty list           Frame IDs
                                                              currently
                                                              allocated to this
                                                              process.

  `open_files`         `List[str]`       Empty list           File paths or
                                                              identifiers for
                                                              files currently
                                                              open by the
                                                              process.
  -----------------------------------------------------------------------------

**Responsibilities** - Tracks process ownership, timing, priority, and
lifecycle state. - Tracks memory frames and files held by the process. -
Supports CPU scheduling and resource cleanup when a process terminates.

## 2. Memory Manager

### `PageFrame`

Represents a physical memory frame and the virtual page, if any,
currently stored in it.

  -----------------------------------------------------------------------
  Attribute         Type              Default           Description
  ----------------- ----------------- ----------------- -----------------
  `frame_id`        `int`             Required          Physical memory
                                                        frame number.

  `page_number`     `Optional[int]`   `None`            Virtual page
                                                        currently loaded
                                                        in the frame, if
                                                        assigned.

  `pid`             `Optional[str]`   `None`            Process ID
                                                        associated with
                                                        the loaded page,
                                                        if assigned.

  `is_modified`     `bool`            `False`           Indicates whether
                                                        the page has been
                                                        modified since
                                                        being loaded or
                                                        last written
                                                        back.

  `last_accessed`   `int`             `0`               Logical time or
                                                        counter
                                                        representing the
                                                        most recent
                                                        access.
  -----------------------------------------------------------------------

**Responsibilities** - Represents physical memory slots. - Associates a
loaded virtual page with its owning process. - Provides metadata that
can support page-replacement decisions and modified-page handling.

## 3. File System Manager

### `FileNode`

Represents a file or directory in the simulated file system.

  -----------------------------------------------------------------------------
  Attribute         Type                    Default           Description
  ----------------- ----------------------- ----------------- -----------------
  `path`            `str`                   Required          Absolute path to
                                                              the file or
                                                              directory.

  `name`            `str`                   Required          File or directory
                                                              name.

  `is_dir`          `bool`                  Required          `True` for a
                                                              directory and
                                                              `False` for a
                                                              regular file.

  `owner_id`        `str`                   Required          Identifier of the
                                                              owning user.

  `permissions`     `str`                   `"rwx"`           Permission
                                                              representation.
                                                              The model does
                                                              not define a
                                                              formal permission
                                                              grammar.

  `size`            `int`                   `0`               Size of the file
                                                              or directory,
                                                              according to the
                                                              file-system
                                                              implementation.

  `content`         `str`                   `""`              Text content for
                                                              a file.

  `parent_path`     `Optional[str]`         `None`            Path to the
                                                              parent directory,
                                                              if one exists.

  `created_at`      `int`                   `0`               Creation
                                                              timestamp or
                                                              logical time.

  `modified_at`     `int`                   `0`               Last-modified
                                                              timestamp or
                                                              logical time.

  `children`        `Dict[str, FileNode]`   Empty dictionary  Child entries for
                                                              a directory,
                                                              keyed by child
                                                              name.
  -----------------------------------------------------------------------------

**Relationships and behavior** - A `FileNode` may reference its parent
through `parent_path`. - A directory can contain child `FileNode`
objects in `children`. - The dictionary key is intended to be the child
name. - The `content` field is intended for file data; directory
behavior should be defined by the file-system manager. - The model does
not itself enforce path consistency, permission checks, or
directory-only child rules.

## 4. Security Manager

### `User`

Represents a user account in the system.

  -----------------------------------------------------------------------
  Attribute         Type              Default           Description
  ----------------- ----------------- ----------------- -----------------
  `user_id`         `str`             Required          User identifier.

  `username`        `str`             Required          Account username.

  `role`            `str`             Required          Role assigned to
                                                        the user, such as
                                                        an administrator
                                                        or standard user
                                                        if supported by
                                                        the
                                                        implementation.

  `permissions`     `List[str]`       Empty list        Permission flags
                                                        assigned to the
                                                        user.
  -----------------------------------------------------------------------

### `SecurityContext`

Represents an active authenticated session or security context.

  -------------------------------------------------------------------------------
  Attribute                 Type              Default           Description
  ------------------------- ----------------- ----------------- -----------------
  `context_id`              `str`             Required          Identifier for
                                                                the active
                                                                session or
                                                                security context.

  `user_id`                 `str`             Required          User associated
                                                                with the context.

  `token`                   `str`             Required          Temporary
                                                                authentication
                                                                token.

  `effective_permissions`   `List[str]`       Empty list        Permissions
                                                                effective during
                                                                the session.
  -------------------------------------------------------------------------------

**Relationships and behavior** - `SecurityContext.user_id` associates a
context with a `User.user_id`. - Effective permissions may be derived
from the user's assigned permissions and session-specific rules; the
derivation is not implemented by these data classes. - Authentication,
token validation, expiration, and authorization enforcement belong to
the security manager.

## 5. Device Manager

### `DeviceRequest`

Represents a process request to perform an operation on a device.

  ------------------------------------------------------------------------
  Attribute          Type              Default           Description
  ------------------ ----------------- ----------------- -----------------
  `request_id`       `str`             Required          Unique
                                                         device-request
                                                         identifier.

  `device_id`        `str`             Required          Identifier of the
                                                         target device,
                                                         such as `DISK_1`.

  `process_id`       `str`             Required          ID of the process
                                                         that submitted
                                                         the request.

  `operation_type`   `str`             Required          Operation
                                                         requested, such
                                                         as a read or
                                                         write. Supported
                                                         values are
                                                         defined by the
                                                         device manager.

  `status`           `str`             `"PENDING"`       Request status.
                                                         The code comments
                                                         list `PENDING`,
                                                         `IN_PROGRESS`,
                                                         `COMPLETED`, and
                                                         `FAILED`.
  ------------------------------------------------------------------------

**Responsibilities** - Links an operation to a target device and
requesting process. - Tracks progress through the device manager's
request lifecycle. - Scheduling policy depends on device type and
manager implementation.

## 6. Network Manager

### `Packet`

Represents a network packet moving between nodes in the simulated
system.

  ---------------------------------------------------------------------------
  Attribute             Type              Default           Description
  --------------------- ----------------- ----------------- -----------------
  `packet_id`           `str`             Required          Unique packet
                                                            identifier.

  `source_node`         `str`             Required          Network node that
                                                            originated the
                                                            packet.

  `dest_node`           `str`             Required          Intended
                                                            destination node.

  `source_process_id`   `str`             Required          ID of the process
                                                            that created or
                                                            sent the packet.

  `payload_size`        `int`             Required          Payload size in
                                                            bytes.

  `hop_limit`           `int`             `64`              Maximum remaining
                                                            hops before the
                                                            packet should be
                                                            discarded, if
                                                            hop-limit
                                                            behavior is
                                                            implemented.

  `creation_time`       `int`             `0`               Creation
                                                            timestamp or
                                                            logical time.

  `status`              `str`             `"QUEUED"`        Packet status.
                                                            The code comments
                                                            list `QUEUED`,
                                                            `TRANSMITTING`,
                                                            `DELIVERED`, and
                                                            `DROPPED`.
  ---------------------------------------------------------------------------

**Responsibilities** - Tracks packet source, destination, size, and
originating process. - Supports packet lifecycle tracking and hop-limit
handling. - Routing, delivery, and status transitions are implemented by
the network manager, not by the data class itself.

## Entity Relationships

The following relationships are represented by identifiers or nested
objects rather than explicit database foreign keys:

  ----------------------------------------------------------------------------------
  Source entity       Attribute             Related entity         Relationship
  ------------------- --------------------- ---------------------- -----------------
  `Process`           `owner_id`            `User.user_id`         A process is
                                                                   owned by a user.

  `Process`           `allocated_frames`    `PageFrame.frame_id`   A process tracks
                                                                   its allocated
                                                                   physical frames.

  `Process`           `open_files`          `FileNode.path`        A process tracks
                                            (intended)             its open files by
                                                                   path or
                                                                   identifier.

  `PageFrame`         `pid`                 `Process.pid`          A frame may be
                                                                   associated with a
                                                                   process.

  `FileNode`          `owner_id`            `User.user_id`         A file or
                                                                   directory is
                                                                   owned by a user.

  `FileNode`          `parent_path`         `FileNode.path`        A node may
                                                                   reference its
                                                                   parent directory.

  `FileNode`          `children`            `FileNode`             A directory may
                                                                   contain child
                                                                   nodes.

  `SecurityContext`   `user_id`             `User.user_id`         A security
                                                                   context belongs
                                                                   to a user.

  `DeviceRequest`     `process_id`          `Process.pid`          A device request
                                                                   is submitted by a
                                                                   process.

  `Packet`            `source_process_id`   `Process.pid`          A packet is
                                                                   associated with
                                                                   its source
                                                                   process.
  ----------------------------------------------------------------------------------

## Data Validation and Implementation Notes

The data classes define structure and default values, but they do not
automatically enforce all system invariants. The managers should
validate the following where appropriate:

1.  **Identifier uniqueness:** IDs such as `pid`, `user_id`, `frame_id`,
    `request_id`, `packet_id`, and `context_id` should be unique within
    their respective namespaces.
2.  **Numeric values:** Times, sizes, priorities, and page numbers
    should follow the ranges and conventions expected by the
    implementation.
3.  **Process lifecycle:** State changes should follow the process
    scheduler's allowed transitions.
4.  **Resource cleanup:** On process termination, allocated frames, open
    files, and pending operations should be handled according to system
    policy.
5.  **Memory consistency:** A frame's `pid` and `page_number` should
    consistently describe the page loaded in that frame.
6.  **File-system consistency:** Paths, parent references, child
    dictionary keys, directory rules, and file sizes should remain
    consistent.
7.  **Permissions:** Permission strings and permission flags should use
    a consistent, documented format, and access checks should be
    enforced by the relevant manager.
8.  **Request and packet statuses:** Status values should be validated
    and transitions should be controlled. They are currently represented
    as strings rather than enums.
9.  **Network hop limit:** Forwarding logic should define when and how
    `hop_limit` is decremented and when a packet is dropped.
10. **Mutable defaults:** `field(default_factory=list)` and
    `field(default_factory=dict)` create separate collections for each
    instance, preventing instances from sharing the same mutable default
    list or dictionary.

## Scope

This document describes the shared data structures shown in the provided
Python code. It does not specify database tables, serialization formats,
scheduling algorithms, routing algorithms, permission semantics, or
manager-specific business logic unless noted explicitly above.
