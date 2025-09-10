# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# libreria zk_manager del repositorio https://github.com/lajonner/zk_manager.git
try:
    from zk import ZK, const
    from zk.finger import Finger
    import traceback
except:
    pass

NO_JOBS = 0
ERROR = 1
COMMIT = 2  # COMMIT,OK
NO_HANDLED = 3
SUPERUSER_ID = 1

OK_SOUND = 0
RETRY_SOUND = 4


class ZkManager(object):

    def __init__(self, ip, port=4370, timeout=5, verbose=False):
        self.conn = None
        self.verbose = verbose
        self.zk = ZK(ip, port=port, timeout=timeout, verbose=self.verbose)

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def __get_info_user(self, user):
        return {
            "UID": user.uid,
            "Name": user.name,
            "Privilege": user.privilege,
            'Password': user.password
        }

    def __get_info_zk(self, conn):
        return {
            'Firmware Version': conn.get_firmware_version(),
            'Serial Number': conn.get_serialnumber(),
            'Platform': conn.get_platform(),
            'MAC': conn.get_mac(),
            'Device Name': conn.get_device_name(),
            'Face Version': conn.get_face_version(),
            'FingerPrint Name': conn.get_fp_version()
        }

    def unpack_finger(self, json):
        return Finger.json_unpack(json)

    def get_device_info(self):
        values = {"info": None, "status": NO_JOBS, "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                info = self.__get_info_zk(self.conn)
                values["info"] = info
                self.conn.enable_device()
                values["status"] = COMMIT
                values["message"] = "OK"
            except Exception as e:
                values["info"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def get_user_info(self, uid):
        values = {"info": None, "status": NO_JOBS, "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                exists_test, exists_user, exists_finger = self.exists(uid)
                if exists_test:
                    info = self.__get_info_user(exists_user)
                    values["info"] = info
                self.conn.enable_device()
                values["status"] = COMMIT
                values["message"] = "OK"
            except Exception as e:
                values["info"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def get_full_users(self):
        values = {"users": {}, "status": NO_JOBS, "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                user_maps = self.__all_users()
                values["users"] = user_maps
                self.conn.enable_device()
                values["status"] = COMMIT
                values["message"] = "OK"
            except Exception as e:
                values["users"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def __all_users(self):
        users = self.conn.get_users()
        fingers = self.conn.get_templates()
        user_maps = {}
        if users:
            for user in users:
                user_maps[user.uid] = {"user": user, "fingers": []}
        if fingers:
            for finger in fingers:
                (user_maps[finger.uid]["fingers"]).append(finger)
        return user_maps

    def exists(self, uid):
        user_maps = self.__all_users()
        USER = user_maps.get(uid, False)
        if not USER:
            return False, None, []
        USER = user_maps[uid]
        exists_user = USER["user"]
        exists_finger = USER["fingers"]
        return True, exists_user, exists_finger

    def exists_fingers(self, all_users, uid, fid):
        user_vals = all_users.get(uid, False)
        if not user_vals:
            return False, None, []
        fingers = user_vals.get('fingers', {})
        for finger in fingers:
            if finger.fid == fid:
                return True, finger, fingers
        return False, None, []

    def create_user(self, uid, name, privilege=0, password='1234', group_id='', user_id=False, card=0):
        values = {"user": None,
                  "fingers": [],
                  "status": NO_JOBS,
                  "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                if not user_id:
                    user_id = uid
                if type(user_id) == str:
                    user_id = str(uid)
                exists_test, exists_user, exists_finger = self.exists(uid)
                if not exists_test:
                    self.zk.set_user(uid=uid, name=name, privilege=privilege, password=password, group_id=group_id,
                                     user_id=user_id, card=card)
                    exists_test, exists_user, exists_finger = self.exists(uid)
                    if exists_test:
                        values["user"] = exists_user
                        values["fingers"] = exists_finger
                        values["status"] = COMMIT
                        values["message"] = "CREATED"
                else:
                    values["user"] = exists_user
                    values["fingers"] = exists_finger
                    values["status"] = NO_HANDLED
                    values["message"] = "ALREADY EXISTS"
                self.conn.enable_device()
            except Exception as e:
                values["user"] = None
                values["fingers"] = []
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def write_user(self, uid, name, privilege=False, password=False, group_id=False, card=False):
        values = {"user": None,
                  "fingers": [],
                  "status": NO_JOBS,
                  "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                exists_test, exists_user, exists_finger = self.exists(uid)
                if not exists_test:
                    values["message"] = "USER NOT FOUND"
                else:
                    privilege = privilege or exists_user.privilege
                    password = password or exists_user.password
                    group_id = group_id or exists_user.group_id
                    card = card or exists_user.card
                    self.zk.set_user(uid=uid, name=name, privilege=privilege, password=password, group_id=group_id,
                                     user_id=exists_user.user_id, card=card)
                    exists_test, exists_user, exists_finger = self.exists(uid)
                    fingers = []
                    values["user"] = exists_user
                    values["fingers"] = exists_finger
                    values["status"] = COMMIT
                    values["message"] = "UPDATED"
                self.conn.enable_device()
            except Exception as e:
                values["fingers"] = []
                values["user"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def delete_user(self, uid):
        values = {"user": None,
                  "fingers": [],
                  "status": NO_JOBS,
                  "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                exists_test, exists_user, exists_finger = self.exists(uid)
                if not exists_test:
                    values["message"] = "USER NOT FOUND"
                else:
                    self.zk.delete_user(uid, exists_user.user_id)
                    values["fingers"] = exists_finger
                    values["user"] = exists_user
                    values["status"] = COMMIT
                    values["message"] = "OK"
                self.conn.enable_device()
            except Exception as e:
                values["user"] = None
                values["fingers"] = []
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def get_attendances(self):
        values = {"attendances": None,
                  "status": NO_JOBS,
                  "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                attendances = self.conn.get_attendance()
                print(attendances, '<<<<<<<<<<<<<<<')
                self.conn.enable_device()
                values["attendances"] = attendances
                values["status"] = COMMIT
                values["message"] = "OK"
            except:
                values["attendances"] = None
                values["status"] = ERROR
                values["message"] = str('Error')
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def clear_attendances(self, read_attendances=True):
        values = {"attendances": None,
                  "status": NO_JOBS,
                  "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                attendances = read_attendances and self.conn.get_attendance() or []
                self.conn.clear_attendance()
                self.conn.enable_device()
                values["attendances"] = attendances
                values["status"] = COMMIT
                values["message"] = "OK"
            except:
                values["attendances"] = None
                values["status"] = ERROR
                values["message"] = str('Error')
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def delete_users(self):
        values = {"users": None,
                  "status": NO_JOBS,
                  "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                users = self.conn.get_users()
                for user in users:
                    if (user.uid != SUPERUSER_ID):
                        self.zk.delete_user(user.uid, user.user_id)
                values["users"] = users
                values["status"] = COMMIT
                values["message"] = "OK"
                self.conn.enable_device()
            except Exception as e:
                values["users"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def set_time_device(self, hours):
        values = {"users": None,
                  "status": NO_JOBS,
                  "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                zktime = self.conn.get_time()
                print(zktime, 'nueva hora', hours)
                self.conn.set_time(hours)
                self.conn.enable_device()
                values["status"] = COMMIT
                values["message"] = "OK"
            except Exception as e:
                values["users"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def restart_service_device(self):
        values = {"users": None,
                  "status": NO_JOBS,
                  "message": None}
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                self.conn.restart()
                self.conn.enable_device()
                values["status"] = COMMIT
                values["message"] = "OK"
            except Exception as e:
                values["users"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def take_fingerprint(self, uid, fid, warning=False):  # finger 0-9
        values = {"user": None,
                  "fingers": [],
                  "status": NO_JOBS,
                  "message": None}
        if fid < 0 or fid > 9:
            values["status"] = ERROR
            values["message"] = "footprints range from 0 to 9 (left to right)"
            return values
        if self.zk:
            try:
                self.conn = self.zk.connect()
                self.conn.disable_device()
                exists_test, exists_user, exists_finger = self.exists(uid)
                print(exists_test, exists_user, exists_finger)
                if not exists_test:
                    values["message"] = "USER NOT FOUND"
                else:
                    values["user"] = exists_user
                    self.conn.delete_user_template(uid, fid)
                    self.conn.reg_event(0xFFFF)  #
                    values["status"] = NO_HANDLED
                    values["message"] = "ENROLLING USER"
                    self._log("ENROLLING USER {}...".format(uid))
                    result_enroll = self.conn.enroll_user(uid, fid)
                    all_users = self.__all_users()
                    exists_finger, finger, fingers = self.exists_fingers(all_users, uid, fid)
                    if exists_finger:
                        if warning:
                            self._log("enroll %s " % (result_enroll,))
                            print(result_enroll)
                            if result_enroll:
                                self.conn.test_voice(OK_SOUND)  # register ok
                                tem = self.conn.get_user_template(uid, fid)
                                print(tem)
                                values["status"] = COMMIT
                                values["message"] = "OK"
                                values["fingers"] = fingers
                            else:
                                values["status"] = ERROR
                                values["message"] = "REINTENTE CON LA TOMA DE HUELLAS"
                                values["fingers"] = fingers
                                self.conn.test_voice(RETRY_SOUND)  # not registered
                        else:
                            values["status"] = COMMIT
                            values["message"] = "OK"
                            values["fingers"] = fingers
                            self.conn.test_voice(OK_SOUND)  # register ok
                    else:
                        values["status"] = ERROR
                        values["message"] = "REINTENTE CON LA TOMA DE HUELLAS"
                        values["fingers"] = fingers
                        self.conn.test_voice(RETRY_SOUND)  # not registered
                self.conn.enable_device()
            except Exception as e:
                values["fingers"] = []
                values["user"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    try:
                        self.conn.cancel_capture()
                        self.conn.enable_device()
                    except Exception as er:
                        self._log(str(er))
                    finally:
                        self.conn.disconnect()
                        return values
                return values
        return values

    def sync_users_from_to(self, from_zkm, type_filter="blacklist", listfilter=[SUPERUSER_ID]):
        values = {"users": None,
                  "status": NO_JOBS,
                  "message": None}

        def test_blacklist(uid, listfilter):
            return (listfilter and (uid not in listfilter))

        def test_existlist(uid, listfilter):
            return (listfilter and (uid in listfilter))

        filter_def = {
            "blacklist": test_blacklist,
            "existlist": test_existlist
        }
        if from_zkm.zk:
            try:
                all_values = from_zkm.get_full_users()
                if (all_values.get("status", NO_JOBS)) == COMMIT:
                    all_users = all_values.get("users", [])
                    self.conn = self.zk.connect()
                    self.conn.disable_device()
                    def_test = filter_def[type_filter]
                    for data_user_ky in all_users:
                        data_user = all_users[data_user_ky]
                        user = data_user["user"]
                        test_list = def_test(user.uid, listfilter)
                        print(user.user_id, user.name, test_list)
                        if test_list:
                            fingers = data_user["fingers"]
                            self.zk.set_user(uid=user.uid, name=user.name, privilege=user.privilege,
                                             password=str(user.uid), group_id=user.group_id, user_id=str(user.uid),
                                             card=user.card)
                            test_user, exists_user, exists_fingers = self.exists(user.uid)
                            if test_user:
                                new_fingers = []
                                for finger in fingers:
                                    newFinger = Finger(exists_user.uid, finger.fid, finger.valid, finger.template)
                                    new_fingers.append(newFinger)
                                self.zk.save_user_template(exists_user, fingers=new_fingers)
                    new_users = self.__all_users()
                    values["status"] = COMMIT
                    values["message"] = "OK"
                    values["users"] = new_users
                    self.conn.enable_device()
            except Exception as e:
                print(str(e))
                values["users"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values

    def sync_users_from_to_pk_user(self, from_zkm, type_filter="blacklist", listfilter=[SUPERUSER_ID]):
        values = {"users": None,
                  "status": NO_JOBS,
                  "message": None}

        def test_blacklist(user_id, listfilter):
            return (listfilter and (user_id not in listfilter))

        def test_existlist(user_id, listfilter):
            return (listfilter and (user_id in listfilter))

        filter_def = {
            "blacklist": test_blacklist,
            "existlist": test_existlist
        }
        pk = SUPERUSER_ID
        if from_zkm.zk:
            try:
                all_values = from_zkm.get_full_users()
                if (all_values.get("status", NO_JOBS)) == COMMIT:
                    all_users = all_values.get("users", [])
                    self.conn = self.zk.connect()
                    self.conn.disable_device()
                    def_test = filter_def[type_filter]
                    for data_user_ky in all_users:
                        data_user = all_users[data_user_ky]
                        user = data_user["user"]
                        new_pk = int(user.user_id)
                        test_list = def_test(new_pk, listfilter)
                        print(new_pk, user.name, test_list)
                        if test_list:
                            fingers = data_user["fingers"]
                            self.zk.set_user(uid=new_pk, name=user.name, privilege=user.privilege,
                                             password=str(user.user_id), group_id=user.group_id, user_id=str(user.uid),
                                             card=user.card)
                            test_user, exists_user, exists_fingers = self.exists(new_pk)
                            if test_user:
                                new_fingers = []
                                for finger in fingers:
                                    newFinger = Finger(new_pk, finger.fid, finger.valid, finger.template)
                                    new_fingers.append(newFinger)
                                self.zk.save_user_template(exists_user, fingers=new_fingers)
                                pk += 1
                    new_users = self.__all_users()
                    values["status"] = COMMIT
                    values["message"] = "OK"
                    values["users"] = new_users
                    self.conn.enable_device()
            except Exception as e:
                print(str(e))
                values["users"] = None
                values["status"] = ERROR
                values["message"] = str(e)
            finally:
                if self.conn:
                    self.conn.disconnect()
        return values
