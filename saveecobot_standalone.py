# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SaveecobotLoader
                                 A QGIS standalone script
 This standalone script loads AQI data from Safeecobot
        copyright            : (C) 2024 by Bundesamt für Strahlenschutz
        email                : mlechner@bfs.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.PyQt.QtCore import QVariant, QDateTime, QUrlQuery, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsApplication, QgsVectorLayer, QgsProject, QgsFeature, QgsPointXY, QgsGeometry, QgsField, QgsCoordinateReferenceSystem, QgsNetworkAccessManager, QgsNetworkReplyContent, QgsVectorFileWriter

import json
import os
import sys
from datetime import datetime

os.environ["QT_QPA_PLATFORM"] = "offscreen"
if sys.argv[1] and sys.argv[1] != "":
    savedir = sys.argv[1]
elif os.path.dirname(os.path.realpath(__file__)) != "/":
    savedir = os.path.dirname(os.path.realpath(__file__))
elif os.path.exists("/opt/standalone_scripts"):
    savedir = "/opt/standalone_scripts"
else:
    print("Can not estimate savedir. Using /")
    savedir = "/"
app = QgsApplication([], True)
# use OS specific paths here!
QgsApplication.setPrefixPath("/usr", True)
sys.path.append("/usr/share/qgis/python/plugins")
QgsApplication.initQgis()

class SaveecobotLoader:
    """QGIS Plugin Implementation."""

    def run(self):
        """Run method that performs all the real work"""
        self.dlg = QVariant()
        self.dlg.sebDataUrlLineEdit = str("https://www.saveecobot.com/storage/maps_data.js")
        self.dlg.sebMarkerDataUrlLineEdit = str("https://www.saveecobot.com/en/maps/marker.json")

        # set default values for dlg
        self.dlg.dateTimeEdit = QDateTime(datetime.utcnow())
        self.dlg.lineEditLayerName = str(datetime.strftime(datetime.utcnow(), '%Y%m%d-%H%M_saveecobot'))
        result = 1
        # See if OK was pressed
        if result:
            sebtimestring = self.dlg.dateTimeEdit.toString('yyyy-MM-ddThhmm:ss')
            markertimestring = self.dlg.dateTimeEdit.toString('yyyy-MM-ddThh-mm:ss')
            sebkey = 'gamma'
            
            # Set up the first GET Request to SaveEcoBot
            sebquery = QUrlQuery()
            sebquery.addQueryItem('date', sebtimestring)
            seburl = QUrl(self.dlg.sebDataUrlLineEdit)
            seburl.setQuery(sebquery)

            manager = QgsNetworkAccessManager()

            sebrequest = QNetworkRequest(seburl)
            response: QgsNetworkReplyContent = manager.blockingGet(sebrequest)
            status_code = response.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            if status_code == 200:
                # Get the content of the response and process it
                sebdata = json.loads(bytes(response.content()))
            else:
                print("SaveEcoBot loader error: Couldn't load data from " + seburl.url())

            # create layer
            vl_name = self.dlg.lineEditLayerName if (self.dlg.lineEditLayerName and len(self.dlg.lineEditLayerName) > 0) else "temporary_saveecobot"
            vl = QgsVectorLayer("Point", vl_name, "memory")
            vl.setCrs(QgsCoordinateReferenceSystem('EPSG:4326'))

            pr = vl.dataProvider()
            # add fields default fields
            pr.addAttributes([QgsField("id", QVariant.Int),
                    QgsField("lon",  QVariant.Double),
                    QgsField("lat", QVariant.Double)])
            # add all other fields i a generic way
            keylist = []
            if 'devices' in sebdata.keys() and isinstance(sebdata['devices'], list):
                for sebdatarow in sebdata['devices']:
                    for key in sebdatarow.keys():
                        if (key not in keylist):
                            keylist.append(key)
                            try:
                                float(sebdatarow[key])
                                pr.addAttributes([QgsField(key, QVariant.Double)])
                            except ValueError:
                                pr.addAttributes([QgsField(key, QVariant.String)])
            else:
                print("SaveEcoBot loader error: No devices list found in data from " + str(seburl))
                exit
                    
            vl.updateFields() # tell the vector layer to fetch changes from the provider
            # add detailfields

            if 'devices' in sebdata.keys() and isinstance(sebdata['devices'], list):
                for sebdatarow in sebdata['devices']:
                    if sebkey in sebdatarow:
                        # add a feature
                        feat = QgsFeature()
                        feat.setFields(vl.fields())
                        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(sebdatarow["n"]),float(sebdatarow["a"]))))
                        featattributes = []
                        for key in feat.fields().names():
                            if key == "id":
                                featattributes.append(int(sebdatarow["i"]))
                            if key == "lon":
                                featattributes.append(float(sebdatarow["a"]))
                            if key == "lat":
                                featattributes.append(float(sebdatarow["n"]))
                        for key in feat.fields().names():
                            if key not in ("id", "device_id", "lon", "lat"):
                                if key in sebdatarow:
                                    if vl.fields().field(key).type() == QVariant.Int:
                                        try:
                                            featattributes.append(int(sebdatarow[key]))
                                        except:
                                            featattributes.append(None)
                                            print("Warning: wrong data type at id " + str(featattributes[0]) + " for attribute " + key + ". value " + str(sebdatarow[key]) + " not imported.")
                                    elif vl.fields().field(key).type() == QVariant.Double:
                                        try:
                                            featattributes.append(float(sebdatarow[key]))
                                        except:
                                            featattributes.append(None)
                                            print("Warning: wrong data type at id " + str(featattributes[0]) + " for attribute " + key + ". value " + str(sebdatarow[key]) + " not imported.")
                                    elif vl.fields().field(key).type() == QVariant.String:
                                        try:
                                            featattributes.append(str(sebdatarow[key]))
                                        except:
                                            featattributes.append(None)
                                            print("Warning: wrong data type at id " + str(featattributes[0]) + " for attribute " + key + ". value " + str(sebdatarow[key]) + " not imported.")
                                    else:
                                        featattributes.append(None)
                                else:
                                    featattributes.append(None)
                        if len(featattributes) == len(vl.fields()):
                            feat.setAttributes(featattributes)
                            pr.addFeatures([feat])
                        else:
                            print("Error: featattributes len for id " + str(featattributes[0]) + " is " + str(len(featattributes)))

            # update layer's extent when new features have been added
            # because change of extent in provider is not propagated to the layer
            vl.updateExtents()
            QgsProject.instance().addMapLayer(vl)
            # add last_updated_at / gamma to layer abstract
            if 'last_updated_at' in sebdata.keys() and 'gamma' in sebdata['last_updated_at']:
                vlm = vl.metadata()
                vlm.setAbstract('gamma latest updated (Ukraine local time): ' + sebdata['last_updated_at']['gamma'])
                vl.setMetadata(vlm)

            pr.addAttributes([QgsField("device_id", QVariant.String),
                    QgsField("latest", QVariant.DateTime),
                    QgsField("history", QVariant.String),
                    QgsField("history_hours", QVariant.Int),
                    QgsField("content", QVariant.String)])
            vl.updateFields() # tell the vector layer to fetch changes from the provider
            vl.startEditing()
            markerquery = QUrlQuery()
            markerquery.addQueryItem('marker_type', 'device')
            markerquery.addQueryItem('pollutant', str(sebkey))
            markerquery.addQueryItem('is_wide', str(1))
            markerquery.addQueryItem('is_iframe', str(0))
            markerquery.addQueryItem('is_widget', str(0))
            markerquery.addQueryItem('rand', markertimestring)
            markerurl = QUrl(self.dlg.sebMarkerDataUrlLineEdit)

            # load detail data for features
            count = vl.featureCount()
            
            for current, feature in enumerate(vl.getFeatures()):
                markerdata = json.loads('{}')
                sfid = str(feature.attribute("id"))
                percent = current / float(count) * 100
                markerquery.addQueryItem('marker_id', sfid)
                markerurl.setQuery(markerquery)
                markerrequest = QNetworkRequest(markerurl)
                response: QgsNetworkReplyContent = manager.blockingGet(markerrequest)
                status_code = response.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                if status_code == 200:
                    # Get the content of the response and process it
                    markerdata = json.loads(bytes(response.content()))
                else:
                    print("SaveEcoBot loader error: Could not load details for " + sfid)
                markerquery.removeQueryItem('marker_id')
                if markerdata != json.loads('{}'):
                    feature.setAttribute("device_id", str(markerdata["marker_data"]["id"]))
                    if (len(markerdata["history"]) > 0):
                        feature.setAttribute("latest", QDateTime.fromString(sorted(markerdata["history"].keys()).pop(), "yyyy-MM-dd hh:mm:ss"))
                        feature.setAttribute("history", str(markerdata["history"]))
                    feature.setAttribute("history_hours", int(markerdata["history_hours"]))
                    feature.setAttribute("content", str(markerdata["content"]))
                    vl.updateFeature(feature)
                percent = current / float(count) * 100
                print(str(current) + "/" + str(count) + " (" + str(round(percent, 1)) + "%) done.")
            vl.commitChanges()

            QgsVectorFileWriter.writeAsVectorFormatV3(vl, savedir + "/" + self.dlg.lineEditLayerName + ".gpkg", QgsProject.instance().transformContext(), QgsVectorFileWriter.SaveVectorOptions())

myseb = SaveecobotLoader()
myseb.run()
# make run return the layer and put save into a new function
QgsApplication.exitQgis()
