import urllib2

from flask import Response
from .zones import Zone
from extensions import db


class HandlerExporter(object):

    def __init__(self):
        self.filename = "alarmdecoder-network-appliance.groovy"
        self.handlerUrl = "https://raw.githubusercontent.com/yhax/alarmdecoder-smartthings/zone.updates/devicetypes/alarmdecoder/alarmdecoder-network-appliance.src/alarmdecoder-network-appliance.groovy"
        self.deviceHandler = None
        self.numberOfZones = 0

        # These are the areas in alarmdecoder-network-appliance.groovy to replace with actual zone data from ====================
        #========================================================================================================================
        self.DO_NOT_DELETE_TEMPLATE_ZONE_NUMBERS = "//DO_NOT_DELETE_TEMPLATE_ZONE_NUMBERS"

        self.DO_NOT_DELETE_TEMPLATE_ZONE_ATTRIBUTES = "//DO_NOT_DELETE_TEMPLATE_ZONE_ATTRIBUTES"

        self.DO_NOT_DELETE_TEMPLATE_ZONE_BYPASS_CMDS = "//DO_NOT_DELETE_TEMPLATE_ZONE_BYPASS_CMDS"

        self.DO_NOT_DELETE_TEMPLATE_ZONE_TILES = "//DO_NOT_DELETE_TEMPLATE_ZONE_TILES"

        self.DO_NOT_DELETE_TEMPLATE_ZONE_DETAILS = "//DO_NOT_DELETE_TEMPLATE_ZONE_DETAILS"

        self.DO_NOT_DELETE_TEMPLATE_ZONE_LOOP = "DO_NOT_DELETE_TEMPLATE_ZONE_LOOP"

        self.DO_NOT_DELETE_TEMPLATE_ZONE_BYPASS_DEFS = "//DO_NOT_DELETE_TEMPLATE_ZONE_BYPASS_DEFS"
        #========================================================================================================================

    def modifyHandler(self):
        # Zones to exclude from configuration, modify as needed
        excluded_zones = [99]

        # Add the database column for the st_id if it is not already there
        try:
            db.session.execute('ALTER TABLE zones ADD COLUMN st_id INTEGER DEFAULT 0;')
        except:
            pass # if this fails, its probably already defined - could be improved

        # Get all the info about the zones - this must be setup before running the generator
        zones = Zone.query.all()
        if len(zones) <= 0:
            return "no zones found"

        # Get the default alarmdecoder-network-appliance.groovy file as a string
        urlResponse = urllib2.urlopen(self.handlerUrl)
        template = urlResponse.read()

        zoneInputs = []
        zoneAttributes = []
        zoneTiles = []
        bypassCommands = []
        bypassFunctions = []

        zoneCounter = 1
        zoneDetailsStr = 'details(["status", "arm_disarm", "stay_disarm", "panic", "fire", "aux",'

        # By setting the default value, we are mapping the zone_id to the zone tracker input id, right away
        for z in zones:
            if z.zone_id not in excluded_zones:
                if z.zone_id is None:
                    continue;

                z.st_id = zoneCounter;
                db.session.add(z)
                db.session.commit()

                zoneInputs.append('input("zonetracker{0}zone", "number", title: "{1}", description: "{2}", defaultValue: "{3}")'.\
                    format(zoneCounter, self.getZoneInfo(z.name, zoneCounter, True), self.getZoneInfo(z.description, zoneCounter, False), z.zone_id))
                zoneAttributes.append('attribute "zoneStatus' + str(zoneCounter)  + '", "string"')
                zoneTiles.append(self.getZoneTile(zoneCounter))
                zoneDetailsStr += '"zoneStatus' + str(zoneCounter) + '", '
                bypassCommands.append('command "bypass' + str(zoneCounter) + '"')
                bypassFunctions.append(self.getBypassDef(zoneCounter))
                zoneCounter += 1

        numberOfZones = zoneCounter - 1 # zero based index
        zoneDetailsStr += '"refresh"])'

        # Replacing the old zone tracker inputs with the new inputs
        newZones = '\n\t\t'.join(zoneInputs)
        template = template.replace(self.DO_NOT_DELETE_TEMPLATE_ZONE_NUMBERS, newZones)
        zoneInputs = None        

        # Replacing the old zone attributes with the new attributes
        newAttributes = '\n\t\t'.join(zoneAttributes)
        template = template.replace(self.DO_NOT_DELETE_TEMPLATE_ZONE_ATTRIBUTES, newAttributes)
        zoneAttributes = None

        # Update bypass commands
        newCommands = '\n\t\t'.join(bypassCommands)
        template = template.replace(self.DO_NOT_DELETE_TEMPLATE_ZONE_BYPASS_CMDS, newCommands)
        bypassCommands = None

        # Replacing the old zone tiles with the new zone tiles
        newTiles = '\n\t\t'.join(zoneTiles)
        template = template.replace(self.DO_NOT_DELETE_TEMPLATE_ZONE_TILES, newTiles)
        zoneTiles = None

        # Updating the zone details with the new zones
        template = template.replace(self.DO_NOT_DELETE_TEMPLATE_ZONE_DETAILS, zoneDetailsStr)

        # Update all zone loops
        template = template.replace(self.DO_NOT_DELETE_TEMPLATE_ZONE_LOOP, str(numberOfZones))

        # Update bypass definitions
        newFunctions = '\n'.join(bypassFunctions)
        template = template.replace(self.DO_NOT_DELETE_TEMPLATE_ZONE_BYPASS_DEFS, newFunctions)
        bypassFunctions = None

        # Update the device handler
        self.deviceHandler = template

    def ReturnResponse(self):
        return Response(self.deviceHandler, mimetype='application/x-gzip', headers= { 'Content-Type': 'application/json', 'Content-Disposition': 'attachment; filename=' + self.filename } )

    def getZoneInfo(self, strToCheck, id, isTitle):
        if strToCheck and strToCheck.strip():
            return strToCheck
        elif isTitle:
            return 'ZoneTracker Sensor #' + str(id)
        
        return 'Zone number to associate with this contact sensor.'

    def getZoneTile(self, index):
        return 'valueTile("zoneStatus{0}", "device.zoneStatus{1}", inactiveLabel: false, width: 1, height: 1) {{\n'.format(index, index) + \
                '\t\t\tstate "default", icon:"", label: \'${{currentValue}}\', action: "bypass{0}", nextState: "default", backgroundColors: [\n'.format(index) + \
                '\t\t\t[value: 0, color: "#ffffff"],\n' + \
                '\t\t\t[value: 1, color: "#ff0000"],\n' + \
                '\t\t\t[value: 99, color: "#ff0000"]\n' + \
                '\t\t\t]\n\t\t}\n'

    def getBypassDef(self, index):
        return 'def bypass{0}() {{\n'.format(index) + \
                '\tbypassN({0})\n'.format(index) + \
                '}\n'