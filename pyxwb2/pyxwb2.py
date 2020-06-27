import jsonschema
import json

from pathlib import Path, PurePath
from jsonpath2 import Path as JPath

from .models.base import Faction, Factions, Ship, Ships
from .models.misc import Actions, Conditions, DamageDeck, ShipStats
from .models.pilot import Pilots, Pilot
from .utils import manifest

_local_path = Path(__file__).parents[0]


def _load_complex_manifest_data(cls, manifest_set, inner_set=None):
    obj = cls()
    for set_file in manifest[manifest_set]:
        with open(PurePath(_local_path, set_file).as_posix(), "r") as f:
            _set = json.load(f)
        try:
            for _dc in _set[inner_set]:
                obj.append(obj._singular.load_data(_dc))
        except (KeyError, TypeError):
            for _dc in _set:
                obj.append(obj._singular.load_data(_dc))

    return obj


class XwingSquadron:

    def __init__(self, trust_source=False):
        self.trust_source = trust_source

        self.name = None
        self.description = None
        self.obstacles = None
        self.points = None
        self.vendor = None
        self.version = None
        self.faction = None
        self.pilots = None

    def import_squad(self, xws):
        """
        Import the xws data to validate the squad

        :param xws: Importing data from either an already imported json file, or pass
                    in a string of the json file to process. This will populate the already
                    initialized Xwb object.
        :return: None
        """

        if isinstance(xws, str):
            with open(xws, "r") as xws_file:
                _xws_data = json.load(xws_file)
        elif isinstance(xws, dict):
            _xws_data = xws
        else:
            raise ValueError("Unable to load data set. Be sure to pass in a string of the filename or"
                             "an already loaded dict from the xws json file.")

        # Validate the schema if we dont trust the source. Other validation happens for required items
        # even if this is bypassed.
        if not self.trust_source:
            self._validate_schema(_xws_data)

        self.version = _xws_data.get("version")
        self.name = _xws_data.get("name")
        self.description = _xws_data.get("description")

        self.faction = Faction.load_data(_xws_data.get("faction"))
        self.pilots = Pilots.load_data(_xws_data.get("pilots"), self.faction)

    @staticmethod
    def _validate_schema(xws_data):
        schema_fn = PurePath(_local_path, "data/xws_schema.json").as_posix()
        with open(schema_fn, "r") as f:
            schema = json.load(f)

        jsonschema.validate(instance=xws_data, schema=schema)


class XwingDataPack:
    def __init__(self):
        self.factions = Factions()
        self.pilots = Pilots()
        self.ships = Ships()
        self.actions = Actions()

        self._load()

    def _load(self):
        factions_jpath = JPath.parse_str("$.pilots.*.faction")
        _factions = [m.current_value for m in factions_jpath.match(manifest)]

        for pilot in manifest["pilots"]:
            _faction = Faction.load_data(pilot["faction"])
            self.factions.append(_faction)
            for ship in pilot["ships"]:
                with open(PurePath(_local_path, ship).as_posix(), "r") as f:
                    ship_data = json.load(f)

                _ship = Ship.load_data(ship_data)
                _ship.faction = _faction
                self.ships.append(_ship)

                for pilot_data in ship_data["pilots"]:
                    _pilot = Pilot.load_data(pilot_data)
                    _pilot.__setattr__("faction", _faction)
                    _pilot.__setattr__("ship", _ship)
                    self.pilots.append(_pilot)

        self.actions = _load_complex_manifest_data(Actions, "actions")

        with open(PurePath(_local_path, manifest["conditions"]).as_posix(), "r") as f:
            self.conditions = Conditions.load_data(json.load(f))

        self.damage_deck = _load_complex_manifest_data(DamageDeck, "damagedecks", "cards")
        self.stats = _load_complex_manifest_data(ShipStats, "stats")

