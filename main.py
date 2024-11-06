import requests
import pyMeow as pm
import tkinter as tk
from tkinter import colorchooser
from threading import Thread
import ctypes

class Offsets:
    m_pBoneArray = 69
    #bone array no work :(

class Colors:
    t_color = pm.get_color("orange")
    ct_color = pm.get_color("cyan")
    black = pm.get_color("black")
    DP = pm.get_color("#4F2A66") 
    grey = pm.fade_color(pm.get_color("#242625"), 0.7)

class Entity:
    def __init__(self, ptr, pawn_ptr, proc):
        self.ptr = ptr
        self.pawn_ptr = pawn_ptr
        self.proc = proc
        self.pos2d = None
        self.head_pos2d = None

    @property
    def name(self):
        return pm.r_string(self.proc, self.ptr + Offsets.m_iszPlayerName)

    @property
    def health(self):
        return pm.r_int(self.proc, self.pawn_ptr + Offsets.m_iHealth)

    @property
    def team(self):
        return pm.r_int(self.proc, self.pawn_ptr + Offsets.m_iTeamNum)

    @property
    def pos(self):
        return pm.r_vec3(self.proc, self.pawn_ptr + Offsets.m_vOldOrigin)

    @property
    def dormant(self):
        return pm.r_bool(self.proc, self.pawn_ptr + Offsets.m_bDormant)

    def bone_pos(self, bone):
        game_scene = pm.r_int64(self.proc, self.pawn_ptr + Offsets.m_pGameSceneNode)
        bone_array_ptr = pm.r_int64(self.proc, game_scene + Offsets.m_pBoneArray)
        return pm.r_vec3(self.proc, bone_array_ptr + bone * 32)

    def wts(self, view_matrix):
        try:
            self.pos2d = pm.world_to_screen(view_matrix, self.pos, 1)
            self.head_pos2d = pm.world_to_screen(view_matrix, self.bone_pos(6), 1)
        except Exception as e:
            print(f"Error converting world to screen: {e}")
            return False
        return True

    @property 
    def distance(self): 
        local_pos = pm.r_vec3(self.proc, self.mod + Offsets.dwLocalPlayerPawn + Offsets.m_vOldOrigin) 
        return pm.vec3_dist(self.pos, local_pos)

class CS2Esp:
    def __init__(self):
        self.proc = pm.open_process("cs2.exe")
        self.mod = pm.get_module(self.proc, "client.dll")["base"]
        self.running = False

        # Initialize offsets
        try:
            offsets_name = ["dwViewMatrix", "dwEntityList", "dwLocalPlayerController", "dwLocalPlayerPawn"]
            offsets = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json").json() # Offsets automatically update.
            [setattr(Offsets, k, offsets["client.dll"][k]) for k in offsets_name]

            client_dll_name = {
                "m_iIDEntIndex": "C_CSPlayerPawnBase",
                "m_hPlayerPawn": "CCSPlayerController",
                "m_fFlags": "C_BaseEntity",
                "m_iszPlayerName": "CBasePlayerController",
                "m_iHealth": "C_BaseEntity",
                "m_iTeamNum": "C_BaseEntity",
                "m_vOldOrigin": "C_BasePlayerPawn",
                "m_pGameSceneNode": "C_BaseEntity",
                "m_bDormant": "CGameSceneNode",
            }
            clientDll = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json").json()
            [setattr(Offsets, k, clientDll["client.dll"]["classes"][client_dll_name[k]]["fields"][k]) for k in client_dll_name]
        except requests.RequestException as e:
            print(f"Error fetching offsets: {e}, If not working within 24 hours raise issue on the github page")


    def it_entities(self):
        ent_list = pm.r_int64(self.proc, self.mod + Offsets.dwEntityList)
        local = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerController)

        for i in range(1, 65):
            try:
                entry_ptr = pm.r_int64(self.proc, ent_list + (8 * (i & 0x7FFF) >> 9) + 16)
                controller_ptr = pm.r_int64(self.proc, entry_ptr + 120 * (i & 0x1FF))

                if controller_ptr == local:
                    continue

                controller_pawn_ptr = pm.r_int64(self.proc, controller_ptr + Offsets.m_hPlayerPawn)
                list_entry_ptr = pm.r_int64(self.proc, ent_list + 0x8 * ((controller_pawn_ptr & 0x7FFF) >> 9) + 16)
                pawn_ptr = pm.r_int64(self.proc, list_entry_ptr + 120 * (controller_pawn_ptr & 0x1FF))
            except Exception as e:
                print(f"Error reading entity data: {e}")
                continue

            yield Entity(controller_ptr, pawn_ptr, self.proc)

    def run(self):
        self.running = True
        pm.overlay_init("Counter-Strike 2", fps=144)

        while pm.overlay_loop() and self.running:
            view_matrix = pm.r_floats(self.proc, self.mod + Offsets.dwViewMatrix, 16)

            pm.begin_drawing()
            pm.draw_fps(0, 0)

            orange_count = 0
            cyan_count = 0

            for ent in self.it_entities():
    if ent.wts(view_matrix) and ent.health > 0 and not ent.dormant:
        color = Colors.ct_color if ent.team != 2 else Colors.t_color
        if ent.team != 2:
            cyan_count += 1
        else:
            orange_count += 1

        head = ent.pos2d["y"] - ent.head_pos2d["y"]
        width = head / 2
        center = width / 2

        # Snapline
        pm.draw_line(
            pm.get_screen_width() / 2,
            pm.get_screen_height() / 2,
            ent.head_pos2d["x"] - center,
            ent.head_pos2d["y"] - center / 2,
            Colors.black,
            3
        )
        pm.draw_line(
            pm.get_screen_width() / 2,
            pm.get_screen_height() / 2,
            ent.head_pos2d["x"] - center,
            ent.head_pos2d["y"] - center / 2,
            color,
        )

        # Box
        pm.draw_rectangle(
            ent.head_pos2d["x"] - center,
            ent.head_pos2d["y"] - center / 2,
            width,
            head + center / 2,
            Colors.grey,
        )
        pm.draw_rectangle_lines(
            ent.head_pos2d["x"] - center,
            ent.head_pos2d["y"] - center / 2,
            width,
            head + center / 2,
            color,
            1.2,
        )

        # Health Bar
        health_bar_length = 50
        health_percentage = ent.health / 100.0
        pm.draw_rectangle(
            ent.head_pos2d["x"] - center,
            ent.head_pos2d["y"] - center / 2 - 10,
            health_bar_length * health_percentage,
            5,
            Colors.green,
        )
        pm.draw_rectangle_lines(
            ent.head_pos2d["x"] - center,
            ent.head_pos2d["y"] - center / 2 - 10,
            health_bar_length,
            5,
            Colors.black,
        )

        # Info
        txt = f"{ent.name} ({ent.health}%) [{ent.distance:.1f}m]"
        pm.draw_text(
            txt,
            ent.head_pos2d["x"] - pm.measure_text(txt, 15) // 2,
            ent.pos2d["y"],
            15,
            Colors.DP,
        )

        # Skull at head position
        pm.draw_text(
            "💀",
            ent.head_pos2d["x"] - 15,  # Adjust X position
            ent.head_pos2d["y"] - 30,  # Adjust Y position above head
            30,
            Colors.red,
        )

            # Display the counts on the overlay
            pm.draw_text(
                f"Terrorists: {orange_count}",
                10,
                pm.get_screen_height() - 100,
                20,
                Colors.t_color,
            )
            pm.draw_text(
                f"Counter-Terrorists: {cyan_count}",
                10,
                pm.get_screen_height() - 80,
                20,
                Colors.ct_color,
            )

            t
            pm.end_drawing()

    def stop(self):
        self.running = False

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CS2 ESP Control")
        self.geometry("450x150")

        self.emoji_label = tk.Label(self, text="👌\n ESP", font=("Helvetica", 36))
        self.emoji_label.pack(pady=10)
        self.after(3000, self.expand_window)  

        self.start_button = tk.Button(self, text="Start ESP", command=self.start_esp)
        self.stop_button = tk.Button(self, text="Stop ESP", command=self.stop_esp)
        self.color_button_t = tk.Button(self, text="Change T Color", command=self.change_color_t)
        self.color_button_ct = tk.Button(self, text="Change CT Color", command=self.change_color_ct)

        self.esp = CS2Esp()
        self.thread = None

    def expand_window(self):
        self.geometry("300x250")  # Expand to the new size
        self.emoji_label.pack_forget()  # Remove the emoji
        self.start_button.pack(pady=5)
        self.stop_button.pack(pady=5)
        self.color_button_t.pack(pady=5)
        self.color_button_ct.pack(pady=5)

    def start_esp(self):
        if self.thread is None or not self.thread.is_alive():
            self.thread = Thread(target=self.esp.run)
            self.thread.start()

    def stop_esp(self):
        self.esp.stop()
        if self.thread is not None:
            self.thread.join()

    def change_color_t(self):
        color = colorchooser.askcolor()[1]
        if color:
            Colors.t_color = pm.get_color(color)

    def change_color_ct(self):
        color = colorchooser.askcolor()[1]
        if color:
            Colors.ct_color = pm.get_color(color)

if __name__ == "__main__":
    app = App()
    app.mainloop()
