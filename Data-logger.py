import re
from bs4 import BeautifulSoup as soup
import threading
import sqlite3
import datetime
import csv
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox

running = False


class Fetch:
    def __init__(self):
        pass

    def fetch_modell(self):
        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\temp.db")
        c = conn.cursor()

        c.execute("SELECT * FROM Modell")
        row = c.fetchone()

        modell = row[0]

        conn.commit()
        c.close()
        conn.close()

        return modell

    def save_csv(self):
        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\larmlogg.db")
        c = conn.cursor()

        c.execute("SELECT * FROM Tid")
        rows = c.fetchall()
        
        with open("G:\\Programming\\Python\\Projects\\Tid.csv", "w") as f:
            writer = csv.writer(f)

            writer.writerow(["Datum", "Modell", "Drifttid", "Stopptid", "Cykelstopp", "Omställning", "Beslag", "Antal",
                             "Kass_höger", "Kass_vänster"])
            for result in rows:
                writer.writerow(result)

        c.execute("SELECT * FROM Larm")
        rows = c.fetchall()

        with open("G:\\Programming\\Python\\Projects\\Larm.csv", "w") as f:
            writer = csv.writer(f)

            writer.writerow(["Datum", "Modell", "Larm", "Stopptid", "Antal"])
            for result in rows:
                writer.writerow(result)

        c.execute("SELECT * FROM BeslagPerTimme")
        rows = c.fetchall()

        with open("G:\\Programming\\Python\\Projects\\BeslagPerTimme.csv", "w") as f:
            writer = csv.writer(f)

            writer.writerow(["Datum", "kl_0", "kl_1", "kl_2", "kl_3", "kl_4", "kl_5", "kl_6", "kl_7", "kl_8", "kl_9",
                             "kl_10", "kl_11", "kl_12", "kl_13", "kl_14", "kl_15", "kl_16", "kl_17", "kl_18", "kl_19",
                             "kl_20", "kl_21", "kl_22", "kl_23"])
            for result in rows:
                writer.writerow(result)
        print("DB saved as csv")
        conn.commit()
        c.close()
        conn.close()


class Larmlogg:
    def __init__(self):
        self.modell = Fetch().fetch_modell()
        self.datum = datetime.datetime.now().strftime("%Y-%m-%d")

        self.beslag_count = 0
        self.larm_counter = 0
        self.senaste = 2
        self.save = 0
        self.freq = 0.1
        self.last_larm = []
        self.larm2temp = []
        self.stopptid_dict = {}
        self.running = False
        self.last = False
        self.first_loop = True
        self.same_larm = False

        self.larm = self.get_data()
        self.update_temp()
        self.update_larmlist()

    def loop(self):

        if running is True:
            threading.Timer(6.0, self.loop).start()

            # Get values from database
            self.drifttid, self.stopptid, self.cykelstopp, self.omstallning, self.beslag, self.antal_larm\
                = self.fetch_tid()
            self.modell = Fetch().fetch_modell()

            # Get data from website
            self.kvar, self.kass_h, self.kass_v = self.get_status()
            self.larm = self.get_data()

            # Check if a unit have been produced
            self.diff = self.difference()
            freq = self.freq
            #Fetch().save_csv()

            # Add all new units to the database BeslagPerTimme
            if self.diff > 0:
                self.beslag_timme()

            # If last loop had active alarm and this loop does not
            if len(self.larm) == 0 and self.last is True:
                # Check if new alarms appeared during last session
                self.ny()
                # Adds new alarms to database
                self.from_temp2larm()
                del self.larm2temp[:]

            self.check_if_same()

            # Runs until first unit is produced at new order
            if self.first_loop is False:
                if self.diff == 0:
                    self.omstallning += freq
                else:
                    self.first_loop = True

            # If its the last loop under current order
            if self.kvar == 0 and self.first_loop is True:
                self.omstallning += freq
                self.first_loop = False

            elif len(self.larm) > 0:
                # Checks if the current alarm have been active for more than 5 minutes
                self.larm_counter += freq
                if round(self.larm_counter, 2) <= 5:
                    # Update time and adds new larms
                    self.update_larm()

                    self.stopptid += freq
                else:
                    self.cykelstopp += freq
                    self.update_larm_cykelstopp()
                    self.ny()
            else:
                self.larm_counter = 0
                print(self.beslag_count)
                if self.beslag_minut() < 10:
                    self.drifttid += freq
                else:
                    self.cykelstopp += freq

            self.update_tid()

            print("Modell: " + str(self.modell))
            print("Larmcounter: " + str(round(self.larm_counter, 2)))
            print("Drifttid: " + str(round(self.drifttid, 2)))
            print("Stopptid: " + str(round(self.stopptid, 2)))
            print("Cykelstopp: " + str(round(self.cykelstopp, 2)))
            print("Omställning: " + str(round(self.omstallning, 2)))
            print("Antal: " + str(self.antal_larm))
            print("Kvar: " + str(self.kvar))
            print("Larm: " + str(self.larm))
            print("______")

    def fetch_tid(self):
        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\larmlogg.db")
        c = conn.cursor()

        c.execute("SELECT Datum, Modell FROM Tid WHERE Datum=? AND Modell=?", (self.datum, self.modell))

        rows = c.fetchone()
        if rows is None or rows[0] != self.datum or rows[1] != self.modell:
            c.execute("INSERT INTO Tid (Datum, Modell, Drifttid, Stopptid, Cykelstopp, Omställning, Beslag, Antal,"
                      " Kass_höger, Kass_vänster) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (self.datum, self.modell, 0, 0, 0, 0, 0, 0, 0, 0))

        c.execute("SELECT Drifttid, Stopptid, Cykelstopp, Omställning, Beslag, Antal, Kass_höger, Kass_vänster"
                  " FROM Tid WHERE Datum=? AND Modell=?", (self.datum, self.modell))
        rows = c.fetchone()

        rowlist = []

        for row in rows:
            rowlist.append(row)

        drifttid = rowlist[0]
        stopptid = rowlist[1]
        cykelstopp = rowlist[2]
        omstallning = rowlist[3]
        beslag = rowlist[4]
        antal_larm = rowlist[5]

        conn.commit()
        c.close()
        conn.close()

        return drifttid, stopptid, cykelstopp, omstallning, beslag, antal_larm

    def get_data(self):
        with open("G:\\Programming\\Python\\Projects\\data.html") as html_file:
            read = soup(html_file, 'lxml')
        larm = []
        try:
            for i in range(1, 11):
                for row in read.find("row", id=i):
                    data = row.text
                    if ":" not in data and "Varning" not in data:
                        data = str.replace(data, "Ã¥", "å").replace("Ã¤", "ä")\
                            .replace("Ã¶", "ö").replace("Ã…", "Å").replace("Ã„", "Ä").replace("Ã–", "Ö")
                        larm.append(data)
        except TypeError:
            pass

        return larm

    def get_status(self):
        with open("G:\\Programming\\Python\\Projects\\status.html") as html_file:
            read = soup(html_file, 'lxml')

        match = read.find("div", id="a_2")
        headline = match.b.text
        find = re.findall('\d+', headline)

        rowlist = []

        for items in find:
            rowlist.append(items)

        kvar = int(rowlist[0])
        kass_h = rowlist[1]
        kass_v = rowlist[2]

        return kvar, kass_h, kass_v

    def difference(self):
        if int(self.kvar) < self.senaste:
            diff = self.senaste - self.kvar
        else:
            diff = 0
        if diff in range(1, 7):
            self.beslag += diff * 2
        else:
            diff = 0

        self.senaste = self.kvar

        return diff

    def save(self):
        save = self.save
        save += self.freq
        if save >= 5:
            Fetch().save_csv()
            save = 0

    def beslag_timme(self):
        hour = datetime.datetime.now().hour

        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\larmlogg.db")
        c = conn.cursor()

        c.execute("SELECT * FROM BeslagPerTimme WHERE Datum=?", (self.datum,))
        row = c.fetchall()

        if len(row) == 0:
            c.execute("INSERT INTO BeslagPerTimme (Datum, kl_0, kl_1, kl_2, kl_3, kl_4, kl_5, kl_6, kl_7, kl_8, kl_9, "
                      "kl_10, kl_11, kl_12, kl_13, kl_14, kl_15, kl_16, kl_17, kl_18, kl_19, kl_20, kl_21, kl_22, kl_23) "
                      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (self.datum, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))

            c.execute("SELECT * FROM BeslagPerTimme WHERE Datum=?", (self.datum,))
            row = c.fetchall()

        timme = list(row[0])
        timme.pop(0)

        for i in range(0, 24):
            if i == hour:
                timme[i] += self.diff * 2

        c.execute("UPDATE BeslagPerTimme SET kl_0=?, kl_1=?, kl_2=?, kl_3=?, kl_4=?, kl_5=?, kl_6=?, kl_7=?, kl_8=?,"
                  " kl_9=?, kl_10=?, kl_11=?, kl_12=?, kl_13=?, kl_14=?, kl_15=?, kl_16=?, kl_17=?, kl_18=?, kl_19=?,"
                  " kl_20=?, kl_21=?, kl_22=?, kl_23=? WHERE Datum=?",
                  (timme[0], timme[1], timme[2], timme[3], timme[4], timme[5], timme[6], timme[7], timme[8], timme[9],
                   timme[10], timme[11], timme[12], timme[13], timme[14], timme[15], timme[16], timme[17], timme[18],
                   timme[19], timme[20], timme[21], timme[22], timme[23], self.datum))

        conn.commit()
        c.close()
        conn.close()

    def check_if_same(self):
        if len(self.larm) > 0:
            if self.last:
                self.same_larm = True
            else:
                self.same_larm = False
                self.last = True

        else:
            self.last = False

    def ny(self):
        # Runs when new larm appears when other larms are already active
        if len(self.last_larm) != 0 and len(self.larm) > len(self.last_larm) or len(self.larm2temp) > 0:
            for items in self.larm:
                if items not in self.last_larm:
                    self.larm2temp.append(items)
            if len(self.larm2temp) > 0:
                self.update_temp()

        self.last_larm[:] = self.larm[:]
        return self.larm2temp

    def update_temp(self):
        # If a new larm becomes active after other larms been active the value is stored here then transfered to Larm DB
        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\temp.db")
        c = conn.cursor()

        c.execute("SELECT Larm FROM Temp")
        rows = c.fetchall()

        db = []
        for row in rows:
            db.append(row[0])

        if self.larm_counter < 5 and len(db) > 0:
            for items in db:
                c.execute("DELETE FROM Temp WHERE Larm=?", (items,))
        else:
            if len(self.larm) != 0:
                for items in self.larm2temp:
                    if items in db:
                        c.execute("SELECT Larm, Tid FROM Temp WHERE Larm=?", (items,))
                        row = c.fetchone()

                        value = list(row)
                        if value[1] < 4.99:
                            value[1] += self.freq
                            c.execute("UPDATE Temp SET Tid=? WHERE Larm=?", (round(value[1], 2), items))
                    else:
                        c.execute("INSERT INTO Temp (Larm, Tid) VALUES (?, ?)", (items, 1))

            if len(self.larm) == 0 and self.last is True:
                for items in db:
                    if items in db not in self.larm2temp:
                        c.execute("SELECT Larm, Tid FROM Temp WHERE Larm=?", (items,))
                        rows = c.fetchone()
                        value = list(rows)
                        self.stopptid_dict[value[0]] = value[1]
                        c.execute("DELETE FROM Temp WHERE Larm=?", (items,))

        conn.commit()
        c.close()
        conn.close()

    def from_temp2larm(self):
        print("FROM TEMP2LARM")
        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\larmlogg.db")
        c = conn.cursor()

        datum = self.datum
        modell = self.modell

        c.execute("SELECT Larm FROM Larm WHERE Datum=? AND Modell=?", (datum, modell))

        rows = [r[0] for r in c.fetchall()]
        larm_db = []

        for row in rows:
            larm_db.append(row)

        print("Larm db" + str(larm_db))

        for items in self.larm2temp:
            for k, v in self.stopptid_dict.items():
                if k == items:
                    new_value = v

            if items in larm_db:
                c.execute("SELECT Stopptid, Antal FROM Larm WHERE Datum=? AND Modell=? AND Larm=?",
                          (datum, modell, items))
                rows = c.fetchone()

                rowlist = []
                for row in rows:
                    rowlist.append(row)

                new_tid = rowlist[0] + new_value
                new_antal = rowlist[1] + 1
                print("UPDATING:" + str(new_value))
                c.execute("UPDATE Larm SET Stopptid=?, Antal=? WHERE Datum=? AND Modell=? AND Larm=?",
                          (new_tid, new_antal, datum, modell, items))

                self.antal_larm += 1
                c.execute("UPDATE Tid SET Antal=? WHERE Datum=? AND Modell=?",
                          (self.antal_larm, datum, modell))
            else:
                c.execute("INSERT INTO Larm (Datum, Modell, Larm, Stopptid, Antal) VALUES (?, ?, ?, ?, ?)",
                          (datum, modell, items, round(new_value, 2), 1))

        conn.commit()
        c.close()
        conn.close()

    def update_larmlist(self):
        with open("G:\\Programming\\Python\\Projects\\larmlist.txt", "r") as readfile:
            read = readfile.read().splitlines()
        larmlist = []
        for items in read:
            items = str.replace(items, "Ã¥", "å").replace("Ã¤", "ä") \
                .replace("Ã¶", "ö").replace("Ã…", "Å").replace("Ã„", "Ä").replace("Ã–", "Ö")
            larmlist.append(items)
        return larmlist

    def update_larm(self):
        larmlist = self.update_larmlist()
        self.nyttlarm = []
        for items in self.larm:
            if items not in larmlist:
                self.nyttlarm.append(str(items))
        if len(self.nyttlarm) > 0:
            self.nytt_larm()

        datum = self.datum
        modell = self.modell
        freq = self.freq

        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\larmlogg.db")
        c = conn.cursor()

        c.execute("SELECT Larm FROM Larm WHERE Datum=? AND Modell=?", (datum, modell))

        rows = [r[0] for r in c.fetchall()]

        larm_db = []
        larm2update = []
        larm2add = []

        try:
            for row in rows:
                larm_db.append(row)
            for items in self.larm:
                if items in larm_db:
                    larm2update.append(items)
                else:
                    larm2add.append(items)
        except TypeError:
            print("TypeError")
            for items in self.larm:
                larm2add.append(items)

        if len(larm2add) > 0:
            for items in larm2add:
                c.execute("INSERT INTO Larm (Datum, Modell, Larm, Stopptid, Antal) VALUES (?, ?, ?, ?, ?)",
                          (datum, modell, items, freq, 1))

        if len(larm2update) > 0:
            for items in larm2update:
                c.execute("SELECT Stopptid, Antal FROM Larm WHERE Datum=? AND Modell=? AND Larm=?",
                          (datum, modell, items))
                rows = c.fetchone()

                rowlist = []
                for row in rows:
                    rowlist.append(row)

                new_tid = rowlist[0] + freq
                new_antal = rowlist[1] + 1

                if self.same_larm:
                    c.execute("UPDATE Larm SET Stopptid=? WHERE Datum=? AND Modell=? AND Larm=?",
                              (round(new_tid, 2), datum, modell, items))
                else:
                    c.execute("UPDATE Larm SET Stopptid=?, Antal=? WHERE Datum=? AND Modell=? AND Larm=?",
                              (round(new_tid, 2), new_antal, datum, modell, items))

                    self.antal_larm += 1
                    c.execute("UPDATE Tid SET Antal=? WHERE Datum=? AND Modell=?",
                              (self.antal_larm, datum, modell))

        del larm2update[:]
        del larm2add[:]
        del larm_db[:]

        self.same_larm = True

        conn.commit()
        c.close()
        conn.close()

    def nytt_larm(self):
        with open("G:\\Programming\\Python\\Projects\\larmlist.txt", "a") as append_larmlist:
            for items in self.nyttlarm:
                print("Nyttlarm: " + str(items))
                items = str.replace(items, "å", "Ã¥").replace("ä", "Ã¤") \
                    .replace("ö", "Ã¶").replace("Å", "Ã…").replace("Ä", "Ã„").replace("Ö", "Ã–")
                append_larmlist.write("\n" + str(items))
                print(self.nyttlarm)

        del self.nyttlarm[:]
        self.update_larmlist()

    def update_larm_cykelstopp(self):
        datum = self.datum
        modell = self.modell
        freq = self.freq
        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\larmlogg.db")
        c = conn.cursor()
        c.execute("SELECT Larm FROM Larm_cykelstopp")
        rows = c.fetchall()
        fetch = []

        for row in rows:
            fetch.append(row[0])

        for items in self.larm:
            if items in fetch:
                try:
                    c.execute("SELECT Cykelstopp FROM Larm_cykelstopp WHERE Datum=? AND Modell=? AND Larm=?",
                              (datum, modell, items))

                    rows = c.fetchone()
                    value = rows[0]
                except TypeError:
                    c.execute("INSERT INTO Larm_cykelstopp (Datum, Modell, Larm, Cykelstopp) VALUES (?, ?, ?, ?)",
                              (datum, modell, items, freq))
                    value = 1
                value += freq
                c.execute("UPDATE Larm_cykelstopp SET Cykelstopp=? WHERE Datum=? AND Modell=? AND Larm=?",
                          (round(value, 2), datum, modell, items))
            else:
                c.execute("INSERT INTO Larm_cykelstopp (Datum, Modell, Larm, Cykelstopp) VALUES (?, ?, ?, ?)",
                          (datum, modell, items, freq))

        conn.commit()
        c.close()
        conn.close()

    def beslag_minut(self):
        if self.diff == 0:
            self.beslag_count += 1
        else:
            self.beslag_count = 0

        return self.beslag_count

    def update_tid(self):
        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\larmlogg.db")
        c = conn.cursor()
        c.execute("UPDATE Tid SET Drifttid=?, Stopptid=?, Cykelstopp=?, Beslag=?, Omställning=?, Kass_Höger=?,"
                  " Kass_Vänster=? WHERE Datum=? AND Modell=?",
                  (round(self.drifttid, 2), round(self.stopptid, 2), round(self.cykelstopp, 2), self.beslag,
                   round(self.omstallning, 2), self.kass_h, self.kass_v, self.datum, self.modell))

        conn.commit()
        c.close()
        conn.close()


class Ui_Larmlogg(object):
    def setupUi(self, gui_Larmlogg):
        gui_Larmlogg.setObjectName("Larmlogg")
        gui_Larmlogg.resize(330, 50)

        self.test = QtWidgets.QPushButton(gui_Larmlogg)
        self.test.setGeometry(QtCore.QRect(130, 130, 71, 21))

        self.xs = QtWidgets.QPushButton(gui_Larmlogg)
        self.xs.setGeometry(QtCore.QRect(10, 15, 71, 21))

        self.s = QtWidgets.QPushButton(gui_Larmlogg)
        self.s.setGeometry(QtCore.QRect(90, 15, 71, 21))

        self.n = QtWidgets.QPushButton(gui_Larmlogg)
        self.n.setGeometry(QtCore.QRect(170, 15, 71, 21))

        self.l = QtWidgets.QPushButton(gui_Larmlogg)
        self.l.setGeometry(QtCore.QRect(250, 15, 71, 21))

        self.start = QtWidgets.QPushButton(gui_Larmlogg)
        self.start.setGeometry(QtCore.QRect(90, 100, 71, 21))

        self.stop = QtWidgets.QPushButton(gui_Larmlogg)
        self.stop.setGeometry(QtCore.QRect(170, 100, 71, 21))

        self.modell_key = QtWidgets.QLabel(gui_Larmlogg)
        self.modell_key.setGeometry(QtCore.QRect(120, 45, 80, 21))

        self.modell_value = QtWidgets.QLabel(gui_Larmlogg)
        self.modell_value.setGeometry(QtCore.QRect(160, 45, 80, 21))

        self.retranslateUi(gui_Larmlogg)
        QtCore.QMetaObject.connectSlotsByName(gui_Larmlogg)

        self.xs.clicked.connect(self.extraStor)
        self.s.clicked.connect(self.stor)
        self.n.clicked.connect(self.normal)
        self.l.clicked.connect(self.liten)
        self.start.clicked.connect(self.start_button)
        self.stop.clicked.connect(self.stop_button)
        self.test.clicked.connect(self.test_button)

    def retranslateUi(self, gui_Larmlogg):
        _translate = QtCore.QCoreApplication.translate
        gui_Larmlogg.setWindowTitle(_translate("Larmlogg", "Larmlogg"))
        self.test.setText(_translate("Larmlogg", "test"))
        self.xs.setText(_translate("Larmlogg", "Extra Stor"))
        self.s.setText(_translate("Larmlogg", "Stor"))
        self.n.setText(_translate("Larmlogg", "Normal"))
        self.l.setText(_translate("Larmlogg", "Liten"))
        self.start.setText(_translate("Larmlogg", "Start"))
        self.stop.setText(_translate("Larmlogg", "Stop"))
        self.modell_key.setText(_translate("Larmlogg", "Modell: "))
        modell = Fetch().fetch_modell()
        self.modell_value.setText(modell)

    def start_button(self):
        global running
        run = Larmlogg()
        if running is False:
            running = True
            run.loop()

    def stop_button(self):
        global running
        running = False
        print("Stopped")

    def extraStor(self, gui_Larmlogg):
        modell = "Extra Stor"
        self.change_modell(modell)
        print(modell)
        self.modell_value.setText(modell)

    def stor(self):
        modell = "Stor"
        self.change_modell(modell)
        print(modell)
        self.modell_value.setText(modell)

    def normal(self):
        global modell
        modell = "Normal"
        self.change_modell(modell)
        print(modell)
        self.modell_value.setText(modell)

    def liten(self):
        modell = "Liten"
        self.change_modell(modell)
        print(modell)
        self.modell_value.setText(modell)

    def change_modell(self, change):
        conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\temp.db")
        c = conn.cursor()

        c.execute("UPDATE Modell SET Modell=?", (change,))

        conn.commit()
        c.close()
        conn.close()

        Fetch().fetch_modell()

    def test_button(self):
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Error")
        msgBox.setText("Save unsuccessful, File is already open in another program")
        msgBox.exec_()
                                  

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    gui_Larmlogg = QtWidgets.QMainWindow()
    ui = Ui_Larmlogg()
    ui.setupUi(gui_Larmlogg)
    gui_Larmlogg.show()
    #ui.start_button()
    sys.exit(app.exec_())
    sys.exit
