from dataclasses import dataclass
from enum import IntFlag, IntEnum, auto
from typing import TYPE_CHECKING, Any, Union

from .patchcanvas import (patchcanvas, PortMode, PortType, BoxType,
                          BoxLayoutMode, BoxSplitMode, PortSubType)

if TYPE_CHECKING:
    from .patchbay_manager import PatchbayManager

# Port Flags as defined by JACK
class JackPortFlag(IntFlag):
    IS_INPUT = 0x01
    IS_OUTPUT = 0x02
    IS_PHYSICAL = 0x04
    CAN_MONITOR = 0x08
    IS_TERMINAL = 0x10
    IS_CONTROL_VOLTAGE = 0x100


class GroupPosFlag(IntFlag):
    # used in some config files,
    # it explains why some numbers are missing.
    SPLITTED = 0x04
    WRAPPED_INPUT = 0x10
    WRAPPED_OUTPUT = 0x20
    HAS_BEEN_SPLITTED = 0x40


class PortTypesViewFlag(IntFlag):
    NONE = 0x00
    AUDIO = 0x01
    MIDI = 0x02
    CV = 0x04
    VIDEO = 0x08
    ALL = AUDIO | MIDI | CV | VIDEO


@dataclass
class TransportPosition:
    frame: int
    rolling: bool
    valid_bbt: bool
    bar: int
    beat: int
    tick: int
    beats_per_minutes: float


class TransportViewMode(IntEnum):
    HOURS_MINUTES_SECONDS = 0
    BEAT_BAR_TICK = 1
    FRAMES = 2


class ToolDisplayed(IntFlag):
    PORT_TYPES_VIEW = auto()
    TRANSPORT_CLOCK = auto()
    TRANSPORT_PLAY_STOP = auto()
    TRANSPORT_TEMPO = auto()
    ZOOM_SLIDER = auto()
    BUFFER_SIZE = auto()
    SAMPLERATE = auto()
    LATENCY = auto()
    XRUNS = auto()
    DSP_LOAD = auto()
    ALL = (PORT_TYPES_VIEW
           | TRANSPORT_CLOCK
           | TRANSPORT_PLAY_STOP
           | TRANSPORT_TEMPO
           | ZOOM_SLIDER
           | BUFFER_SIZE
           | SAMPLERATE
           | LATENCY
           | XRUNS
           | DSP_LOAD)
    
    def to_save_string(self) -> str:
        ''' returns a string containing all flags names
            separated with pipe symbol.'''
        all_strs = list[str]()
        
        for flag in ToolDisplayed:
            if flag is ToolDisplayed.ALL:
                continue

            if self & flag:
                all_strs.append(flag.name)
            else:
                all_strs.append('~' + flag.name)
        
        return '|'.join(all_strs)
    
    def filtered_by_string(self, string: str) -> 'ToolDisplayed':
        '''returns another ToolDisplayed with value filtered
           by string where string contains flags names separated with pipe symbol
           as given by to_save_string method.'''
        return_td = ToolDisplayed(self.value)
        
        for disp_str in string.split('|'):
            delete = False
            if disp_str.startswith('~'):
                delete = True
                disp_str = disp_str[1:]

            if disp_str in ToolDisplayed._member_names_:
                if delete:
                    return_td &= ~ToolDisplayed[disp_str]
                else:
                    return_td |= ToolDisplayed[disp_str]

        return return_td


class GroupPos:
    port_types_view: PortTypesViewFlag = PortTypesViewFlag.NONE
    group_name: str = ""
    null_zone: str = ""
    in_zone: str = ""
    out_zone: str = ""
    null_xy: tuple[int, int]
    in_xy: tuple[int, int]
    out_xy: tuple[int, int]
    flags: int = 0
    layout_modes: dict[PortMode, BoxLayoutMode]
    fully_set: bool = True
    
    def __init__(self):
        self.null_xy = (0, 0)
        self.in_xy = (0, 0)
        self.out_xy = (0, 0)
        self.layout_modes = dict[PortMode, BoxLayoutMode]()
    
    @staticmethod
    def _is_point(value: Any) -> bool:
        if not isinstance(value, (list, tuple)):
            return False
        
        if len(value) != 2:
            return False
        
        for v in value:
            if not isinstance(v, int):
                return False
        return True

    @staticmethod
    def from_serialized_dict(src: dict[str, Any]) -> 'GroupPos':
        port_types_view = src['port_types_view']
        group_name = src['group_name']
        null_zone = src['null_zone']
        out_zone = src['out_zone']
        in_zone = src['in_zone']
        null_xy = src['null_xy']
        in_xy = src['in_xy']
        out_xy = src['out_xy']
        flags = src['flags']
        layout_modes = src['layout_modes']
        
        gpos = GroupPos()
        
        if isinstance(port_types_view, int):
            gpos.port_types_view = PortTypesViewFlag(
                port_types_view & PortTypesViewFlag.ALL)
        if isinstance(group_name, str):
            gpos.group_name = group_name
        if isinstance(null_zone, str):
            gpos.null_zone = null_zone
        if isinstance(in_zone, str):
            gpos.in_zone = in_zone
        if isinstance(out_zone, str):
            gpos.out_zone = out_zone
        if GroupPos._is_point(null_xy):
            gpos.null_xy = tuple(null_xy)
        if GroupPos._is_point(in_xy):
            gpos.in_xy = tuple(in_xy)
        if GroupPos._is_point(out_xy):
            gpos.out_xy = tuple(out_xy)
        if isinstance(flags, int):
            try:
                gpos.flags = GroupPosFlag(flags)
            except:
                pass

        if isinstance(layout_modes, dict):
            for key, value in layout_modes.items():
                try:
                    gpos.layout_modes[PortMode(int(key))] = BoxLayoutMode(int(value))
                except:
                    pass
        
        return gpos

    def copy(self) -> 'GroupPos':
        group_pos = GroupPos()
        group_pos.__dict__ = self.__dict__.copy()
        return group_pos

    def eat(self, other: 'GroupPos'):
        self.__dict__ = other.__dict__.copy()

    def as_serializable_dict(self):
        return {'port_types_view': int(self.port_types_view),
                'group_name': self.group_name,
                'null_zone': self.null_zone,
                'in_zone': self.in_zone,
                'out_zone': self.out_zone,
                'null_xy': self.null_xy,
                'in_xy': self.in_xy,
                'out_xy': self.out_xy,
                'flags': self.flags,
                'layout_modes': self.layout_modes}
        
    def set_layout_mode(self, port_mode: PortMode, layout_mode: BoxLayoutMode):
        self.layout_modes[port_mode] = layout_mode

    def get_layout_mode(self, port_mode: PortMode) -> BoxLayoutMode:
        if port_mode in self.layout_modes.keys():
            return self.layout_modes[port_mode]
        return BoxLayoutMode.AUTO


class PortgroupMem:
    group_name: str = ""
    port_type: PortType = PortType.NULL
    port_mode: PortMode = PortMode.NULL
    port_names: list[str]
    above_metadatas: bool = False
    
    def __init__(self):
        self.port_names = list[str]()

    @staticmethod
    def from_serialized_dict(src: dict[str, Any]) -> 'PortgroupMem':
        pg_mem = PortgroupMem()

        try:
            pg_mem.group_name = str(src['group_name'])
            pg_mem.port_type = PortType(src['port_type'])
            pg_mem.port_mode = PortMode(src['port_mode'])
            pg_mem.port_names = [str(a) for a in src['port_names']]
            pg_mem.above_metadatas = bool(src['above_metadatas'])
        except:
            pass

        return pg_mem

    def has_a_common_port_with(self, other: 'PortgroupMem') -> bool:
        if (self.port_type is not other.port_type
                or self.port_mode is not other.port_mode
                or self.group_name != other.group_name):
            return False
        
        for port_name in self.port_names:
            if port_name in other.port_names:
                return True
        
        return False
    
    def as_serializable_dict(self) -> dict[str, Any]:
        return {
            'group_name': self.group_name,
            'port_type': self.port_type,
            'port_mode': self.port_mode,
            'port_names': self.port_names,
            'above_metadatas': self.above_metadatas
        }


class Connection:
    def __init__(self, manager: 'PatchbayManager', connection_id: int,
                 port_out: 'Port', port_in: 'Port'):
        self.manager = manager
        self.connection_id = connection_id
        self.port_out = port_out
        self.port_in = port_in
        self.in_canvas = False

    def port_type(self) -> PortType:
        return self.port_out.type

    def full_type(self) -> tuple[PortType, PortSubType]:
        port_out_type, port_out_subtype = self.port_out.full_type()
        port_in_type, port_in_subtype = self.port_in.full_type()
        return (port_out_type, port_out_subtype | port_in_subtype)
        
    def shown_in_port_types_view(self, port_types_view: PortTypesViewFlag) -> bool:
        if self.port_out.type is PortType.MIDI_JACK:
            return bool(port_types_view & PortTypesViewFlag.MIDI)
        
        if (self.port_out.type is PortType.AUDIO_JACK
                and self.port_in.type is PortType.AUDIO_JACK):
            if (self.port_out.subtype is PortSubType.CV
                    and self.port_in.subtype is PortSubType.CV): 
                return bool(port_types_view & PortTypesViewFlag.CV)
            if (self.port_out.subtype is PortSubType.REGULAR
                    and self.port_in.subtype is PortSubType.REGULAR):
                return bool(port_types_view & PortTypesViewFlag.AUDIO)
        
        return False

    def add_to_canvas(self):
        if self.manager.very_fast_operation:
            return

        if self.in_canvas:
            return

        if not self.manager.port_type_shown(self.full_type()):
            return

        self.in_canvas = True

        patchcanvas.connect_ports(
            self.connection_id,
            self.port_out.group_id, self.port_out.port_id,
            self.port_in.group_id, self.port_in.port_id)

    def remove_from_canvas(self):
        if self.manager.very_fast_operation:
            return

        if not self.in_canvas:
            return

        patchcanvas.disconnect_ports(self.connection_id)
        self.in_canvas = False

    def semi_hide(self, yesno: bool):
        if not self.in_canvas:
            return
        
        patchcanvas.semi_hide_connection(
            self.connection_id, yesno)
    
    def set_in_front(self):
        if not self.in_canvas:
            return
        
        patchcanvas.set_connection_in_front(self.connection_id)


class Port:
    display_name = ''
    group_id = -1
    portgroup_id = 0
    prevent_stereo = False
    last_digit_to_add = ''
    in_canvas = False
    order = None
    uuid = 0 # will contains the real JACK uuid

    # given by JACK metadatas
    pretty_name = ''
    mdata_portgroup = ''
    mdata_signal_type = ''

    def __init__(self, manager: 'PatchbayManager', port_id: int, name: str,
                 port_type: PortType, flags: int, uuid: int):
        self.manager = manager
        self.port_id = port_id
        self.full_name = name
        self.type = port_type
        self.flags = flags
        self.uuid = uuid
        self.subtype = PortSubType.REGULAR

        if (self.type is PortType.AUDIO_JACK
                and self.flags & JackPortFlag.IS_CONTROL_VOLTAGE):
            self.subtype = PortSubType.CV
        elif (self.type is PortType.MIDI_JACK
                and self.full_name.startswith(('a2j:', 'Midi-Bridge:'))):
            self.subtype = PortSubType.A2J

    def mode(self) -> PortMode:
        if self.flags & JackPortFlag.IS_OUTPUT:
            return PortMode.OUTPUT
        elif self.flags & JackPortFlag.IS_INPUT:
            return PortMode.INPUT
        else:
            return PortMode.NULL

    def full_type(self) -> tuple[PortType, PortSubType]:
        return (self.type, self.subtype)
    
    def short_name(self) -> str:
        if self.full_name.startswith('a2j:'):
            long_name = self.full_name.partition(':')[2]
            if ': ' in long_name:
                # normal case for a2j
                return long_name.partition(': ')[2]

        if self.full_name.startswith('Midi-Bridge:'):
            # supress 'Midi-Bridge:' at port name begginning
            long_name = self.full_name.partition(':')[2]
            if ') ' in long_name:
                # normal case, name is after ') '
                return long_name.partition(') ')[2]

            if ': ' in long_name:
                # pipewire jack.filter_name = True
                # Midi-bridge names starts with 'MidiBridge:ClientName:'
                return long_name.partition(': ')[2]

        return self.full_name.partition(':')[2]

    def add_the_last_digit(self):
        self.display_name += ' ' + self.last_digit_to_add
        self.last_digit_to_add = ''
        self.rename_in_canvas()

    def add_to_canvas(self):
        if self.manager.very_fast_operation:
            return
        
        if self.in_canvas:
            return

        if not self.manager.port_type_shown(self.full_type()):
            return

        display_name = self.display_name
        
        if self.pretty_name:
            display_name = self.pretty_name
        
        if not self.manager.use_graceful_names:
            display_name = self.short_name()

        self.in_canvas = True

        patchcanvas.add_port(
            self.group_id, self.port_id, display_name,
            self.mode(), self.type, self.subtype)

    def remove_from_canvas(self):
        if self.manager.very_fast_operation:
            return
        
        if not self.in_canvas:
            return

        patchcanvas.remove_port(self.group_id, self.port_id)
        self.in_canvas = False

    def rename_in_canvas(self):
        if not self.in_canvas:
            return

        display_name = self.display_name
        if self.pretty_name:
            display_name = self.pretty_name

        if not self.manager.use_graceful_names:
            display_name = self.short_name()

        patchcanvas.rename_port(
            self.group_id, self.port_id, display_name)

    def select_in_canvas(self):
        if not self.in_canvas:
            return
        
        patchcanvas.select_port(self.group_id, self.port_id)

    def __lt__(self, other: 'Port'):
        if self.type != other.type:
            return (self.type < other.type)

        if self.subtype is not other.subtype:
            return self.subtype < other.subtype

        # if self.mode() != other.mode():
        #     return (self.mode() < other.mode())

        if self.order is None and other.order is None:
            return self.port_id < other.port_id
        if self.order is None:
            return False
        if other.order is None:
            return True

        return bool(self.order < other.order)


class Portgroup:
    # Portgroup is a stereo pair of ports
    # but could be a group of more ports
    def __init__(self, manager: 'PatchbayManager', group_id: int,
                 portgroup_id: int, port_mode: PortMode, ports: tuple[Port]):
        self.manager = manager
        self.group_id = group_id
        self.portgroup_id = portgroup_id
        self.port_mode = port_mode
        self.ports = tuple(ports)

        self.mdata_portgroup = ''
        self.above_metadatas = False

        self.in_canvas = False

        for port in self.ports:
            port.portgroup_id = portgroup_id

    def port_type(self):
        if not self.ports:
            return PortType.NULL

        return self.ports[0].type

    def full_type(self) -> tuple[PortType, PortSubType]:
        if not self.ports:
            return (PortType.NULL, PortSubType.REGULAR)
        
        return self.ports[0].full_type()

    def update_ports_in_canvas(self):
        for port in self.ports:
            port.rename_in_canvas()

    def sort_ports(self):
        port_list = list(self.ports)
        port_list.sort()
        self.ports = tuple(port_list)

    def add_to_canvas(self):
        if self.manager.very_fast_operation:
            return

        if self.in_canvas:
            return
    
        if not self.manager.port_type_shown(self.full_type()):
            return

        if len(self.ports) < 2:
            return

        for port in self.ports:
            if not port.in_canvas:
                return

        self.in_canvas = True

        patchcanvas.add_portgroup(
            self.group_id, self.portgroup_id,
            self.port_mode, self.ports[0].type, self.ports[0].subtype,
            [port.port_id for port in self.ports])

    def remove_from_canvas(self):
        if self.manager.very_fast_operation:
            return
        
        if not self.in_canvas:
            return

        patchcanvas.remove_portgroup(self.group_id, self.portgroup_id)
        self.in_canvas = False


class Group:
    def __init__(self, manager: 'PatchbayManager', group_id: int,
                 name: str, group_position: GroupPos):
        self.manager = manager
        self.group_id = group_id
        self.name = name
        self.display_name = name
        self.ports = list[Port]()
        self.portgroups = list[Portgroup]()
        self._is_hardware = False
        self.client_icon = ''
        self.a2j_group = False
        self.in_canvas = False
        self.current_position = group_position
        self.uuid = 0
        
        self.has_gui = False
        self.gui_visible = False

        self.mdata_icon = ''

    def __repr__(self) -> str:
        return f"Group({self.name})"

    def update_ports_in_canvas(self):
        for port in self.ports:
            port.rename_in_canvas()

    def add_to_canvas(self, split=BoxSplitMode.UNDEF):
        if self.in_canvas:
            return

        box_type, icon_name = self._get_box_type_and_icon()

        do_split = bool(self.current_position.flags & GroupPosFlag.SPLITTED)
        split = BoxSplitMode.YES if do_split else BoxSplitMode.NO

        gpos = self.current_position

        self.display_name = self.display_name.replace('.0/', '/').replace('_', ' ')
        
        display_name = self.name
        if self.manager.use_graceful_names:
            display_name = self.display_name
        
        layout_modes_ = dict[PortMode, BoxLayoutMode]()
        for port_mode in (PortMode.INPUT, PortMode.OUTPUT, PortMode.BOTH):
            layout_modes_[port_mode] = gpos.get_layout_mode(port_mode.value)
        
        patchcanvas.add_group(
            self.group_id, display_name, split,
            box_type, icon_name, layout_modes=layout_modes_,
            null_xy=gpos.null_xy, in_xy=gpos.in_xy, out_xy=gpos.out_xy)

        self.in_canvas = True

        if do_split:
            gpos.flags |= GroupPosFlag.HAS_BEEN_SPLITTED
            patchcanvas.wrap_group_box(
                self.group_id, PortMode.INPUT,
                bool(gpos.flags & GroupPosFlag.WRAPPED_INPUT),
                animate=False)
            patchcanvas.wrap_group_box(
                self.group_id, PortMode.OUTPUT,
                bool(gpos.flags & GroupPosFlag.WRAPPED_OUTPUT),
                animate=False)
        else:
            patchcanvas.wrap_group_box(
                self.group_id, PortMode.NULL,
                bool(gpos.flags & GroupPosFlag.WRAPPED_INPUT
                     and gpos.flags & GroupPosFlag.WRAPPED_OUTPUT),
                animate=False)
            
        if self.has_gui:
            patchcanvas.set_optional_gui_state(self.group_id, self.gui_visible)

    def remove_from_canvas(self):
        if not self.in_canvas:
            return

        patchcanvas.remove_group(self.group_id)
        self.in_canvas = False

    def redraw_in_canvas(self):
        if not self.in_canvas:
            return
        
        patchcanvas.redraw_group(self.group_id)

    def update_name_in_canvas(self):
        if not self.in_canvas:
            return
        
        display_name = self.name
        if self.manager.use_graceful_names:
            display_name = self.display_name
        
        patchcanvas.rename_group(self.group_id, display_name)

    def _get_box_type_and_icon(self) -> tuple[BoxType, str]:
        box_type = BoxType.APPLICATION
        icon_name = self.name.partition('.')[0].lower()

        if self._is_hardware:
            box_type = BoxType.HARDWARE
            icon_name = ''
            if self.a2j_group or self.display_name in ("Midi-Bridge", "a2j"):
                icon_name = "a2j"

        if self.client_icon:
            box_type = BoxType.CLIENT
            icon_name = self.client_icon

        if (self.name.startswith("PulseAudio ")
                and not self.client_icon):
            if "sink" in self.name.lower():
                box_type = BoxType.MONITOR
                icon_name = 'monitor_playback'
            elif "source" in self.name.lower():
                box_type = BoxType.MONITOR
                icon_name = 'monitor_capture'

        elif (self.name.endswith(" Monitor")
                and not self.client_icon):
            # this group is (probably) a pipewire Monitor group
            box_type = BoxType.MONITOR
            icon_name = 'monitor_playback'
        
        if self.mdata_icon:
            icon_name = self.mdata_icon

        return (box_type, icon_name)

    def semi_hide(self, yesno: bool):
        if not self.in_canvas:
            return 
        
        patchcanvas.semi_hide_group(self.group_id, yesno)

    def set_in_front(self):
        if not self.in_canvas:
            return
        
        patchcanvas.set_group_in_front(self.group_id)

    def get_number_of_boxes(self) -> int:
        if not self.in_canvas:
            return 0

        return patchcanvas.get_number_of_boxes(self.group_id)

    def select_filtered_box(self, n_select=0):
        if not self.in_canvas:
            return
        
        patchcanvas.select_filtered_group_box(self.group_id, n_select)

    def set_optional_gui_state(self, visible: bool):
        self.has_gui = True
        self.gui_visible = visible
        
        if not self.in_canvas:
            return
        
        patchcanvas.set_optional_gui_state(self.group_id, visible)

    def remove_all_ports(self):
        if self.in_canvas:
            for portgroup in self.portgroups:
                portgroup.remove_from_canvas()

            for port in self.ports:
                port.remove_from_canvas()

        self.portgroups.clear()
        self.ports.clear()

    def add_port(self, port: Port):
        port.group_id = self.group_id
        port_full_name = port.full_name

        if (port_full_name.startswith('a2j:')
                and not port.flags & JackPortFlag.IS_PHYSICAL):
            port_full_name = port_full_name.partition(':')[2]
        port.display_name = port_full_name.partition(':')[2]

        if not self.ports:
            # we are adding the first port of the group
            if port.flags & JackPortFlag.IS_PHYSICAL:
                self._is_hardware = True

            if not self.current_position.fully_set:
                if self._is_hardware:
                    self.current_position.flags |= GroupPosFlag.SPLITTED
                self.current_position.fully_set = True
                self.save_current_position()

        self.ports.append(port)
        self.manager._ports_by_name[port.full_name] = port

    def remove_port(self, port: Port):
        if port in self.ports:
            self.ports.remove(port)
        
        if self.manager._ports_by_name.get(port.full_name):
            self.manager._ports_by_name.pop(port.full_name)

    def remove_portgroup(self, portgroup: Portgroup):
        if portgroup in self.portgroups:
            portgroup.remove_from_canvas()
            for port in portgroup.ports:
                port.portgroup_id = 0
            self.portgroups.remove(portgroup)

    def portgroup_memory_added(self, portgroup_mem: PortgroupMem):
        if portgroup_mem.group_name != self.name:
            return

        remove_set = set[Portgroup]()

        # first remove any existing portgroup with one of the porgroup_mem ports
        for portgroup in self.portgroups:
            if (portgroup.port_mode is not portgroup_mem.port_mode
                    or portgroup.port_type() is not portgroup_mem.port_type):
                continue

            for port in portgroup.ports:
                if port.short_name() in portgroup_mem.port_names:
                    remove_set.add(portgroup)

        for portgroup in remove_set:
            self.remove_portgroup(portgroup)

        # add a portgroup if all needed ports are present and consecutive
        port_list = list[Port]()

        for port in self.ports:
            if (port.mode() is not portgroup_mem.port_mode
                    or port.type is not portgroup_mem.port_type):
                continue

            if port.short_name() == portgroup_mem.port_names[len(port_list)]:
                port_list.append(port)

                if len(port_list) == len(portgroup_mem.port_names):
                    # all ports are presents, create the portgroup
                    portgroup = self.manager.new_portgroup(
                        self.group_id, port.mode(), port_list)
                    self.portgroups.append(portgroup)
                    portgroup.add_to_canvas()
                    break

            elif port_list:
                # here it is a port breaking the consecutivity of the portgroup
                break

    def save_current_position(self):
        self.manager.save_group_position(self.current_position)

    def set_group_position(self, group_position: GroupPos, view_change=False):
        if not self.in_canvas:
            return

        ex_gpos_flags = self.current_position.flags
        self.current_position = group_position
        gpos = self.current_position

        for port_mode, layout_mode in group_position.layout_modes.items():
            patchcanvas.set_group_layout_mode(
                self.group_id, port_mode, layout_mode)

        patchcanvas.move_group_boxes(
            self.group_id, gpos.null_xy, gpos.in_xy, gpos.out_xy)

        prevent_overlap = not view_change

        # restore split and wrapped modes
        if gpos.flags & GroupPosFlag.SPLITTED:
            if not ex_gpos_flags & GroupPosFlag.SPLITTED:
                patchcanvas.split_group(self.group_id)

            patchcanvas.wrap_group_box(
                self.group_id, PortMode.INPUT,
                bool(gpos.flags & GroupPosFlag.WRAPPED_INPUT),
                prevent_overlap=prevent_overlap)
            patchcanvas.wrap_group_box(
                self.group_id, PortMode.OUTPUT,
                bool(gpos.flags & GroupPosFlag.WRAPPED_OUTPUT),
                prevent_overlap=prevent_overlap)
        else:
            patchcanvas.wrap_group_box(
                self.group_id, PortMode.NULL,
                bool(gpos.flags & (GroupPosFlag.WRAPPED_INPUT
                                   | GroupPosFlag.WRAPPED_OUTPUT)),
                prevent_overlap=prevent_overlap)

            if ex_gpos_flags & GroupPosFlag.SPLITTED:
                patchcanvas.animate_before_join(self.group_id)

    def set_layout_mode(self, port_mode: PortMode, layout_mode: BoxLayoutMode):
        self.current_position.set_layout_mode(port_mode, layout_mode)
        self.save_current_position()

        if not self.in_canvas:
            return
        
        patchcanvas.set_group_layout_mode(self.group_id, port_mode, layout_mode)

    def wrap_box(self, port_mode: int, yesno: bool):
        wrap_flag = GroupPosFlag.WRAPPED_OUTPUT | GroupPosFlag.WRAPPED_INPUT
        if port_mode == PortMode.INPUT:
            wrap_flag = GroupPosFlag.WRAPPED_INPUT
        elif port_mode == PortMode.OUTPUT:
            wrap_flag = GroupPosFlag.WRAPPED_OUTPUT

        if yesno:
            self.current_position.flags |= wrap_flag
        else:
            self.current_position.flags &= ~wrap_flag

        self.save_current_position()

        if not self.in_canvas:
            return

        patchcanvas.wrap_group_box(self.group_id, port_mode, yesno)

    def set_client_icon(self, icon_name: str, from_metadata=False):
        if from_metadata:
            self.mdata_icon = icon_name
        else:
            self.client_icon = icon_name
        
        box_type, ex_icon_name = self._get_box_type_and_icon()
        
        if self.in_canvas:
            patchcanvas.set_group_icon(
                self.group_id, box_type, icon_name)

    def get_pretty_client(self) -> str:
        for client_name in ('firewire_pcm', 'a2j',
                            'Hydrogen', 'ardour', 'Ardour', 'Qtractor',
                            'SooperLooper', 'sooperlooper', 'Luppp',
                            'seq64', 'calfjackhost', 'rakarrack-plus',
                            'seq192', 'Non-Mixer', 'jack_mixer'):
            if self.name == client_name:
                return client_name

            if self.name.startswith(client_name + '.'):
                return client_name
            
            name = self.name.partition('/')[0]
            if name == client_name:
                return client_name
            
            if name.startswith(client_name + '_'):
                if name.replace(client_name + '_', '', 1).isdigit():
                    return client_name
            
            if ' (' in name and name.endswith(')'):
                name = name.partition(' (')[0]
                if name == client_name:
                    return client_name
                
                if name.startswith(client_name + '_'):
                    if name.replace(client_name + '_', '', 1).isdigit():
                        return client_name

        return ''

    def graceful_port(self, port: Port):
        def split_end_digits(name: str) -> tuple[str, str]:
            num = ''
            while name and name[-1].isdigit():
                num = name[-1] + num
                name = name[:-1]

            if num.startswith('0') and num not in ('0', '09'):
                num = num[1:]

            return (name, num)

        def cut_end(name: str, *ends: str) -> str:
            for end in ends:
                if name.endswith(end):
                    return name.rsplit(end)[0]
            return name

        client_name = self.get_pretty_client()

        if (not client_name
                and port.full_name.startswith(('a2j:', 'Midi-Bridge:'))
                and port.flags & JackPortFlag.IS_PHYSICAL):
            client_name = 'a2j'

        display_name = port.short_name()
        s_display_name = display_name

        if client_name == 'firewire_pcm':
            if '(' in display_name and ')' in display_name:
                after_para = display_name.partition('(')[2]
                display_name = after_para.rpartition(')')[0]
                display_name, num = split_end_digits(display_name)

                if num:
                    if display_name.endswith(':'):
                        display_name = display_name[:-1]
                    display_name += ' ' + num
            else:
                display_name = display_name.partition('_')[2]
                display_name = cut_end(display_name, '_in', '_out')
                display_name = display_name.replace(':', ' ')
                display_name, num = split_end_digits(display_name)
                display_name = display_name + num

        elif client_name == 'Hydrogen':
            if display_name.startswith('Track_'):
                display_name = display_name.replace('Track_', '', 1)

                num, udsc, name = display_name.partition('_')
                if num.isdigit():
                    display_name = num + ' ' + name

            if display_name.endswith('_Main_L'):
                display_name = display_name.replace('_Main_L', ' L', 1)
            elif display_name.endswith('_Main_R'):
                display_name = display_name.replace('_Main_R', ' R', 1)

        elif client_name == 'a2j':
            display_name, num = split_end_digits(display_name)
            if num:
                if display_name.endswith(' MIDI '):
                    display_name = cut_end(display_name, ' MIDI ')

                    if num == '1':
                        port.last_digit_to_add = '1'
                    else:
                        display_name += ' ' + num

                elif display_name.endswith(' Port-'):
                    display_name = cut_end(display_name, ' Port-')

                    if num == '0':
                        port.last_digit_to_add = '0'
                    else:
                        display_name += ' ' + num

        elif client_name in ('ardour', 'Ardour'):
            if '/TriggerBox/' in display_name:
                display_name = '▸ ' + display_name.replace('/TriggerBox/', '/', 1)
            
            for pt in ('audio', 'midi'):
                if display_name == f"physical_{pt}_input_monitor_enable":
                    display_name = "physical monitor"
                    break
            else:
                display_name, num = split_end_digits(display_name)
                if num:
                    display_name = cut_end(display_name,
                                        '/audio_out ', '/audio_in ',
                                        '/midi_out ', '/midi_in ')
                    if num == '1':
                        port.last_digit_to_add = '1'
                    else:
                        display_name += ' ' + num

        elif client_name == 'Qtractor':
            display_name, num = split_end_digits(display_name)
            if num:
                display_name = cut_end(display_name,
                                       '/in_', '/out_')
                if num == '1':
                    port.last_digit_to_add = '1'
                else:
                    display_name += ' ' + num
        
        elif client_name == 'Non-Mixer':
            display_name, num = split_end_digits(display_name)
            if num:
                display_name = cut_end(display_name, '/in-', '/out-')
                
                if num == '1':
                    port.last_digit_to_add = '1'
                else:
                    display_name += ' ' + num
        
        elif client_name == 'jack_mixer':
            prefix, out, side = display_name.rpartition(' Out')
            if out and side in (' L', ' R', ''):
                display_name = prefix + side
                        
        elif client_name in ('SooperLooper', 'sooperlooper'):
            display_name, num = split_end_digits(display_name)
            if num:
                display_name = cut_end(display_name,
                                       '_in_', '_out_')
                if num == '1':
                    port.last_digit_to_add = '1'
                else:
                    display_name += ' ' + num

        elif client_name == 'Luppp':
            if display_name.endswith('\n'):
                display_name = display_name[:-1]

            display_name = display_name.replace('_', ' ')

        elif client_name == 'seq64':
            display_name = display_name.replace('seq64 midi ', '', 1)

        elif client_name == 'seq192':
            display_name = display_name.replace('seq192 ', '', 1)

        elif client_name == 'calfjackhost':
            display_name, num = split_end_digits(display_name)
            if num:
                display_name = cut_end(display_name,
                                       ' Out #', ' In #')

                display_name += " " + num

        elif client_name == 'rakarrack-plus':
            if display_name.startswith('rakarrack-plus '):
                display_name = display_name.replace('rakarrack-plus ', '', 1)
            display_name = display_name.replace('_', ' ')

        elif not client_name:
            display_name = display_name.replace('_', ' ')
            if display_name.lower().endswith(('-left', ' left')):
                display_name = display_name[:-5] + ' L'
            elif display_name.lower().endswith(('-right', ' right')):
                display_name = display_name[:-6] + ' R'
            elif display_name.lower() == 'left in':
                display_name = 'In L'
            elif display_name.lower() == 'right in':
                display_name = 'In R'
            elif display_name.lower() == 'left out':
                display_name = 'Out L'
            elif display_name.lower() == 'right out':
                display_name = 'Out R'

            if display_name.startswith('Audio'):
                display_name = display_name.replace('Audio ', '')

        # reduce graceful name for pipewire Midi-Bridge with
        # option jack.filter_name = true
        if (port.full_name.startswith('Midi-Bridge')
                and display_name.startswith(('capture_', 'playback_'))):
            display_name = display_name.partition('_')[2]

        port.display_name = display_name if display_name else s_display_name

    def add_portgroup(self, portgroup: Portgroup):
        self.portgroups.append(portgroup)

    def change_port_types_view(self):
        # first add group to canvas if not already
        self.add_to_canvas()

        for portgroup in self.portgroups:
            if not self.manager.port_type_shown(portgroup.full_type()):
                portgroup.remove_from_canvas()

        for port in self.ports:
            if not self.manager.port_type_shown(port.full_type()):
                port.remove_from_canvas()

        for port in self.ports:
            port.add_to_canvas()

        for portgroup in self.portgroups:
            portgroup.add_to_canvas()

        # remove group from canvas if no visible ports
        for port in self.ports:
            if port.in_canvas:
                break
        else:
            self.remove_from_canvas()

    def stereo_detection(self, port: Port) -> Union[Port, None]:
        if port.type != PortType.AUDIO_JACK or port.subtype != PortSubType.REGULAR:
            return

        # find the last port with same type and mode in the group
        for other_port in reversed(self.ports):
            if other_port == port:
                continue

            if (other_port.type == port.type
                    and other_port.subtype == port.subtype
                    and other_port.mode() == port.mode()
                    and not other_port.portgroup_id
                    and not other_port.prevent_stereo):
                for portgroup_mem in self.manager.portgroups_memory:
                    if (portgroup_mem.group_name == self.name
                        and portgroup_mem.port_mode == other_port.mode()
                        and portgroup_mem.port_type == other_port.type
                        and other_port.short_name() in portgroup_mem.port_names):
                        # other_port (left) is in a remembered portgroup
                        # prevent stereo detection
                        return
                break
        else:
            return

        may_match_set = set[str]()

        port_name = port.full_name.replace(self.name + ':', '', 1)
        other_port_name = other_port.full_name.replace(self.name + ':', '', 1)

        if port.flags & JackPortFlag.IS_PHYSICAL:
            # force stereo detection for system ports
            # it forces it for firewire long and strange names
            may_match_set.add(other_port_name)

        elif port_name[-1].isdigit():
            # Port ends with digit
            base_port = port_name[:-1]
            in_num = port_name[-1]

            while base_port[-1].isdigit():
                in_num = base_port[-1] + in_num
                base_port = base_port[:-1]

            # if Port ends with Ldigits or Rdigits
            if base_port.endswith('R'):
                may_match_set.add(base_port[:-1] + 'L' + in_num)
            else:
                may_match_set.add(base_port + str(int(in_num) -1))

                if int(in_num) in (1, 2):
                    if base_port.endswith((' ', ('_'))):
                        may_match_set.add(base_port[:-1])
                    else:
                        may_match_set.add(base_port)
        else:
            # Port ends with non digit
            if port_name.endswith('R'):
                may_match_set.add(port_name[:-1] + 'L')
                if len(port_name) >= 2:
                    if port_name[-2] == ' ':
                        may_match_set.add(port_name[:-2])
                    else:
                        may_match_set.add(port_name[:-1])

            elif port_name.endswith('right'):
                may_match_set.add(port_name[:-5] + 'left')

            elif port_name.endswith('Right'):
                may_match_set.add(port_name[:-5] + 'Left')

            elif port_name.endswith('(Right)'):
                may_match_set.add(port_name[:-7] + '(Left)')

            elif port_name.endswith('.r'):
                may_match_set.add(port_name[:-2] + '.l')

            elif port_name.endswith('_r'):
                may_match_set.add(port_name[:-2] + '_l')

            elif port_name.endswith('_r\n'):
                may_match_set.add(port_name[:-3] + '_l\n')

            for x in ('out', 'Out', 'output', 'Output', 'in', 'In',
                      'input', 'Input', 'audio input', 'audio output'):
                if port_name.endswith('R ' + x):
                    may_match_set.add('L ' + x)

                elif port_name.endswith('right ' + x):
                    may_match_set.add('left ' + x)

                elif port_name.endswith('Right ' + x):
                    may_match_set.add('Left ' + x)

        if other_port_name in may_match_set:
            return other_port

    def check_for_portgroup_on_last_port(self):
        if not self.ports:
            return

        last_port = self.ports[-1]
        last_port_name = last_port.short_name()

        # check in the saved portgroups if we need to make a portgroup
        # or prevent stereo detection
        for portgroup_mem in self.manager.portgroups_memory:
            if (portgroup_mem.group_name == self.name
                    and portgroup_mem.port_type == last_port.type
                    and portgroup_mem.port_mode == last_port.mode()
                    and last_port_name == portgroup_mem.port_names[-1]):
                if (len(portgroup_mem.port_names) == 1
                    or portgroup_mem.port_names.index(last_port_name) + 1
                        != len(portgroup_mem.port_names)):
                    return

                port_list = list[Port]()

                for port in self.ports:
                    if (port.type == last_port.type
                            and port.mode() == last_port.mode()):
                        if (len(portgroup_mem.port_names) > len(port_list)
                                and port.short_name()
                                == portgroup_mem.port_names[len(port_list)]):
                            port_list.append(port)

                            if len(port_list) == len(portgroup_mem.port_names):
                                portgroup = self.manager.new_portgroup(
                                    self.group_id, port.mode(), port_list)
                                self.portgroups.append(portgroup)
                                for port in port_list:
                                    if not port.in_canvas:
                                        break
                                else:
                                    portgroup.add_to_canvas()

                        elif port_list:
                            return

        # detect left audio port if it is a right one
        other_port = self.stereo_detection(last_port)
        if other_port is not None:
            portgroup = self.manager.new_portgroup(
                self.group_id, last_port.mode(), (other_port, last_port))
            self.add_portgroup(portgroup)

            if self.in_canvas:
                portgroup.add_to_canvas()

    def check_for_display_name_on_last_port(self):
        if not self.ports:
            return

        last_port = self.ports[-1]
        last_digit = last_port.full_name[-1]

        if last_digit not in ('1', '2'):
            return

        for port in reversed(self.ports[:-1]):
            if (port.type == last_port.type
                    and port.mode() == last_port.mode()
                    and port is not last_port):
                if (port.full_name[:-1] == last_port.full_name[:-1]
                        and ((port.last_digit_to_add == '0'
                              and last_digit == '1'))
                             or (port.last_digit_to_add == '1'
                                 and last_digit == '2')):
                        port.add_the_last_digit()
                break

    def sort_ports_in_canvas(self):
        already_optimized = self.manager.optimized_operation
        self.manager.optimize_operation(True)

        conn_list = list[Connection]()

        if not self.manager.very_fast_operation:
            for conn in self.manager.connections:
                for port in self.ports:
                    if (port in (conn.port_out, conn.port_in)
                            and conn not in conn_list):
                        conn_list.append(conn)
            
            for connection in conn_list:
                connection.remove_from_canvas()
            
            for portgroup in self.portgroups:
                portgroup.remove_from_canvas()

            for port in self.ports:
                port.remove_from_canvas()
        
        self.ports.sort()

        # search and remove existing portgroups with non consecutive ports
        portgroups_to_remove = list[Portgroup]()

        for portgroup in self.portgroups:
            search_index = 0
            previous_port = None
            seems_ok = False

            for port in self.ports:
                if not seems_ok and port is portgroup.ports[search_index]:
                    if (port.mdata_portgroup != portgroup.mdata_portgroup
                            and not portgroup.above_metadatas):
                        portgroups_to_remove.append(portgroup)
                        break

                    if (not portgroup.above_metadatas and not search_index
                            and previous_port is not None
                            and previous_port.mdata_portgroup
                            and previous_port.mdata_portgroup == port.mdata_portgroup):
                        # previous port had the same portgroup metadata
                        # that this port. we need to remove this portgroup.
                        portgroups_to_remove.append(portgroup)
                        break

                    search_index += 1
                    if search_index == len(portgroup.ports):
                        # all ports of portgroup are consecutive
                        # but still exists the risk that metadatas says
                        # that the portgroup has now more ports
                        seems_ok = True
                        if (portgroup.above_metadatas
                                or not portgroup.mdata_portgroup):
                            break

                elif search_index:
                    if (seems_ok
                            and (port.mdata_portgroup != previous_port.mdata_portgroup
                                 or port.type != portgroup.port_type()
                                 or port.mode() != portgroup.port_mode)):
                        # port after the portgroup has not to make
                        # the portgroup higher. We keep this portgroup
                        break

                    # this port breaks portgroup ports consecutivity.
                    # note that ports have been just sorted by type and mode
                    # so no risk that this port is falsely breaking portgroup
                    portgroups_to_remove.append(portgroup)
                    break

                previous_port = port
            else:
                if not seems_ok:
                    portgroups_to_remove.append(portgroup)

        for portgroup in portgroups_to_remove:
            self.remove_portgroup(portgroup)

        # add missing portgroups aboving metadatas from portgroup memory
        for portgroup_mem in self.manager.portgroups_memory:
            if not portgroup_mem.above_metadatas:
                continue

            if portgroup_mem.group_name != self.name:
                continue

            founded_ports = list[Port]()

            for port in self.ports:
                if (not port.portgroup_id
                        and port.type == portgroup_mem.port_type
                        and port.mode() == portgroup_mem.port_mode
                        and port.short_name()
                            == portgroup_mem.port_names[len(founded_ports)]):
                    founded_ports.append(port)
                    if len(founded_ports) == len(portgroup_mem.port_names):
                        new_portgroup = self.manager.new_portgroup(
                            self.group_id, port.mode(), founded_ports)
                        self.portgroups.append(new_portgroup)
                        break

                elif founded_ports:
                    break

        # detect and add portgroups given from metadatas
        portgroups_mdata = list[dict]() # list of dicts

        for port in self.ports:
            if port.mdata_portgroup:
                pg_mdata = None
                if portgroups_mdata:
                    pg_mdata = portgroups_mdata[-1]

                if not port.portgroup_id:
                    if (pg_mdata is not None
                            and pg_mdata['pg_name'] == port.mdata_portgroup
                            and pg_mdata['port_type'] == port.type
                            and pg_mdata['port_mode'] == port.mode()):
                        pg_mdata['ports'].append(port)
                    else:
                        portgroups_mdata.append(
                            {'pg_name': port.mdata_portgroup,
                             'port_type': port.type,
                             'port_mode': port.mode(),
                             'ports':[port]})
        
        for pg_mdata in portgroups_mdata:
            if len(pg_mdata['ports']) < 2:
                continue

            new_portgroup = self.manager.new_portgroup(
                self.group_id, pg_mdata['port_mode'], pg_mdata['ports'])
            new_portgroup.mdata_portgroup = pg_mdata['pg_name']
            self.portgroups.append(new_portgroup)
        
        # add missing portgroups from portgroup memory
        for portgroup_mem in self.manager.portgroups_memory:
            if portgroup_mem.above_metadatas:
                continue

            if portgroup_mem.group_name != self.name:
                continue

            founded_ports = list[Port]()

            for port in self.ports:
                if (not port.portgroup_id
                        and port.type == portgroup_mem.port_type
                        and port.mode() == portgroup_mem.port_mode
                        and port.short_name()
                            == portgroup_mem.port_names[len(founded_ports)]):
                    founded_ports.append(port)
                    if len(founded_ports) == len(portgroup_mem.port_names):
                        new_portgroup = self.manager.new_portgroup(
                            self.group_id, port.mode(), founded_ports)
                        self.portgroups.append(new_portgroup)
                        break

                elif founded_ports:
                    break
        
        if not self.manager.very_fast_operation:
            # ok for re-adding all items to canvas
            for port in self.ports:
                port.add_to_canvas()

            for portgroup in self.portgroups:
                portgroup.add_to_canvas()
        
            for connection in conn_list:
                connection.add_to_canvas()
        
        if not already_optimized:
            self.manager.optimize_operation(False)
            self.redraw_in_canvas()

    def add_all_ports_to_canvas(self):
        for port in self.ports:
            port.add_to_canvas()

        for portgroup in self.portgroups:
            portgroup.add_to_canvas()
