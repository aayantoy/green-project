import flet as ft
import socket
import concurrent.futures
import time
import threading

# --- LOGIKA NETWORK ---

class NetworkScanner:
    def __init__(self):
        self.timeout = 1.0
        self.max_workers = 100 # Dikurangi sedikit agar HP tidak panas

    def scan_port(self, ip, port):
        """Fungsi dasar cek port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False

    def check_subnet(self, subnet_octet):
        """Logic Scan Luas: Cek apakah subnet aktif (Scan host 1-100 cukup)"""
        # Scan 1-50 host pertama dulu untuk efisiensi
        target_hosts = range(1, 51) 
        target_ports = [80, 8080] # Fokus HTTP biasa
        
        prefix = f"192.168.{subnet_octet}"
        
        for host in target_hosts:
            ip = f"{prefix}.{host}"
            for port in target_ports:
                if self.scan_port(ip, port):
                    return (True, ip) # Ketemu satu, langsung lapor aktif
        return (False, None)

    def check_host(self, ip):
        """Logic Scan Detail Router"""
        if self.scan_port(ip, 80):
            return ip
        return None

# --- APLIKASI UTAMA FLET ---

def main(page: ft.Page):
    page.title = "NetHunter Tools"
    page.theme_mode = ft.ThemeMode.DARK # Tampilan Dark Mode Hacker Style
    page.padding = 20
    page.window_width = 400
    page.window_height = 700

    scanner = NetworkScanner()
    
    # === VARIABEL & UI ELEMENTS UNTUK TAB 1 (SCAN LUAS) ===
    txt_start_sub = ft.TextField(label="Start Subnet (ex: 0)", value="0", width=140, keyboard_type=ft.KeyboardType.NUMBER)
    txt_end_sub = ft.TextField(label="End Subnet (ex: 10)", value="5", width=140, keyboard_type=ft.KeyboardType.NUMBER)
    
    list_result_luas = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)
    btn_scan_luas = ft.ElevatedButton("MULAI RADAR SUBNET", icon=ft.icons.RADAR, width=300)
    progress_luas = ft.ProgressBar(width=300, visible=False)
    status_luas = ft.Text("Siap memindai...", color=ft.colors.GREY)

    # === LOGIC TAB 1 ===
    def run_scan_luas(e):
        try:
            start = int(txt_start_sub.value)
            end = int(txt_end_sub.value)
        except:
            status_luas.value = "Error: Input harus angka!"
            page.update()
            return

        list_result_luas.controls.clear()
        btn_scan_luas.disabled = True
        progress_luas.visible = True
        status_luas.value = f"Memindai Subnet 192.168.{start}.x s/d {end}.x ..."
        page.update()

        # Jalankan di Thread agar UI tidak macet
        def process_scan():
            subnets_to_check = range(start, end + 1)
            total = len(subnets_to_check)
            
            # Kita loop satu per satu subnet agar progress bar kerasa
            for idx, sub in enumerate(subnets_to_check):
                # Update status realtime
                status_luas.value = f"Memeriksa 192.168.{sub}.x ({idx+1}/{total})"
                page.update()
                
                is_active, sample_ip = scanner.check_subnet(sub)
                
                if is_active:
                    # Menambahkan Card hasil temuan
                    list_result_luas.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"Subnet AKTIF: 192.168.{sub}.x", weight="bold", color=ft.colors.GREEN),
                                ft.Text(f"Contoh Device: {sample_ip}", size=12),
                                ft.ElevatedButton("Salin ke Scanner Detail", 
                                                  on_click=lambda _, s=sub: copy_to_tab2(s), 
                                                  height=30)
                            ]),
                            padding=10,
                            border=ft.border.all(1, ft.colors.GREEN_400),
                            border_radius=5,
                            margin=5
                        )
                    )
                    page.update()
            
            # Selesai
            btn_scan_luas.disabled = False
            progress_luas.visible = False
            status_luas.value = "Pemindaian Radar Selesai."
            page.update()

        threading.Thread(target=process_scan, daemon=True).start()

    btn_scan_luas.on_click = run_scan_luas

    # Fungsi Helper: Copy IP Subnet ke Tab 2 otomatis
    def copy_to_tab2(subnet_val):
        txt_target_network.value = f"192.168.{subnet_val}"
        page.snack_bar = ft.SnackBar(ft.Text(f"Subnet {subnet_val} disalin ke Tab Scan Detail!"))
        page.snack_bar.open = True
        tabs.selected_index = 1 # Pindah tab otomatis
        page.update()


    # === VARIABEL & UI ELEMENTS UNTUK TAB 2 (SCAN ROUTER) ===
    txt_target_network = ft.TextField(label="Prefix Network (ex: 192.168.100)", 
                                      hint_text="Tanpa angka host terakhir", 
                                      width=250)
    list_result_router = ft.Column(scroll=ft.ScrollMode.AUTO, height=350)
    btn_scan_router = ft.ElevatedButton("SCAN TOTAL 1-254", icon=ft.icons.SEARCH, width=300)
    progress_router = ft.ProgressBar(width=300, visible=False)
    status_router = ft.Text("Menunggu target...", color=ft.colors.GREY)

    # === LOGIC TAB 2 ===
    def run_scan_router(e):
        net_prefix = txt_target_network.value.strip()
        # Validasi sederhana
        if net_prefix.endswith('.'): net_prefix = net_prefix[:-1]
        
        list_result_router.controls.clear()
        btn_scan_router.disabled = True
        progress_router.visible = True
        status_router.value = f"Memburu host hidup di {net_prefix}.1-254..."
        page.update()

        def process_router_scan():
            ips_to_scan = [f"{net_prefix}.{i}" for i in range(1, 255)]
            found_count = 0
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=scanner.max_workers) as executor:
                # Kirim jobs
                future_to_ip = {executor.submit(scanner.check_host, ip): ip for ip in ips_to_scan}
                
                # Saat job selesai satu per satu
                for future in concurrent.futures.as_completed(future_to_ip):
                    ip_result = future.result()
                    if ip_result:
                        found_count += 1
                        list_result_router.controls.append(
                            ft.ListTile(
                                leading=ft.Icon(ft.icons.ROUTER, color=ft.colors.BLUE),
                                title=ft.Text(f"http://{ip_result}"),
                                subtitle=ft.Text("Port 80 Open (Web Admin)"),
                                on_click=lambda _, x=ip_result: page.set_clipboard(f"http://{x}") 
                                # Klik list akan copy url
                            )
                        )
                        page.update()
            
            btn_scan_router.disabled = False
            progress_router.visible = False
            status_router.value = f"Selesai. Ditemukan {found_count} device aktif."
            page.update()

        threading.Thread(target=process_router_scan, daemon=True).start()

    btn_scan_router.on_click = run_scan_router


    # === LAYOUT TABS ===
    tab_1 = ft.Tab(
        text="Cari Subnet",
        icon=ft.icons.LOCATION_SEARCHING,
        content=ft.Column([
            ft.Container(height=10),
            ft.Text("Radar Area (Subnet Scanner)", size=16, weight="bold"),
            ft.Row([txt_start_sub, txt_end_sub], alignment=ft.MainAxisAlignment.CENTER),
            btn_scan_luas,
            progress_luas,
            status_luas,
            ft.Divider(),
            list_result_luas
        ], alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    tab_2 = ft.Tab(
        text="Scan Detail",
        icon=ft.icons.NETWORK_CHECK,
        content=ft.Column([
            ft.Container(height=10),
            ft.Text("Detail Scanner (Host Hunter)", size=16, weight="bold"),
            txt_target_network,
            btn_scan_router,
            progress_router,
            status_router,
            ft.Divider(),
            ft.Text("*Klik hasil untuk copy link", size=10, italic=True),
            list_result_router
        ], alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[tab_1, tab_2],
        expand=1,
    )

    page.add(tabs)

ft.app(target=main)