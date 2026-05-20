-- Seed de demo OperacionesRanger
USE db_aae4a2_ranger;

-- 1. Configuración de turnos
INSERT IGNORE INTO ot_configuracion_turnos (tipo_turno, hora_inicio, hora_fin, descripcion, activo) VALUES
('DIURNO',   '06:00:00', '18:00:00', 'Turno diurno estándar (06:00 - 18:00)', 1),
('NOCTURNO', '18:00:00', '06:00:00', 'Turno nocturno estándar (18:00 - 06:00)', 1);

-- 2. Cliente
INSERT INTO ot_clientes (codigo, nombre, rnc, telefono, email, direccion, contacto_nombre, contacto_telefono, activo)
VALUES ('CLI001', 'BANCO POPULAR DOMINICANO', '101012345', '809-544-5000', 'seguridad@bpd.com.do',
        'Av. John F. Kennedy 20, Santo Domingo', 'Lic. Marcelo Mejía', '809-544-5001', 1);

-- 3. Ubicaciones
INSERT INTO ot_ubicaciones (cliente_id, codigo, nombre, direccion, telefono, activo) VALUES
((SELECT id FROM ot_clientes WHERE codigo='CLI001'), 'UB001', 'Sucursal Naco', 'Av. Tiradentes 32, Naco', '809-544-5050', 1),
((SELECT id FROM ot_clientes WHERE codigo='CLI001'), 'UB002', 'Sucursal Piantini', 'Av. Winston Churchill 95, Piantini', '809-544-5060', 1);

-- 4. Puestos
INSERT INTO ot_puestos (ubicacion_id, codigo, nombre, descripcion, cantidad_guardianes, requiere_turno_diurno, requiere_turno_nocturno, activo) VALUES
((SELECT id FROM ot_ubicaciones WHERE codigo='UB001'), 'P001', 'Entrada Principal Naco',  'Garita principal entrada vehicular',     1, 1, 1, 1),
((SELECT id FROM ot_ubicaciones WHERE codigo='UB001'), 'P002', 'Bóveda Naco',             'Acceso bóveda principal nocturno',       1, 0, 1, 1),
((SELECT id FROM ot_ubicaciones WHERE codigo='UB002'), 'P003', 'Entrada Piantini',        'Lobby principal sucursal Piantini',      1, 1, 0, 1),
((SELECT id FROM ot_ubicaciones WHERE codigo='UB002'), 'P004', 'Parqueo Piantini',        'Estación de control vehicular',          1, 1, 1, 1);

-- 5. Feriados 2026 RD (NACIONAL)
INSERT INTO ot_feriados (fecha, nombre, tipo, descripcion) VALUES
('2026-01-01', 'Año Nuevo', 'NACIONAL', 'Inicio del año'),
('2026-01-06', 'Día de los Santos Reyes', 'NACIONAL', 'Reyes Magos'),
('2026-01-21', 'Nuestra Señora de la Altagracia', 'NACIONAL', 'Patrona nacional'),
('2026-01-26', 'Día de Duarte', 'NACIONAL', 'Natalicio Juan Pablo Duarte'),
('2026-02-27', 'Día de la Independencia', 'NACIONAL', 'Aniversario de la Independencia Nacional'),
('2026-05-01', 'Día del Trabajo', 'NACIONAL', 'Día Internacional del Trabajo'),
('2026-08-16', 'Día de la Restauración', 'NACIONAL', 'Restauración de la República'),
('2026-09-24', 'Nuestra Señora de las Mercedes', 'NACIONAL', 'Patrona de la República'),
('2026-11-06', 'Día de la Constitución', 'NACIONAL', 'Constitución dominicana'),
('2026-12-25', 'Navidad', 'NACIONAL', 'Natividad del Señor');

-- 6. Incentivos por puesto (permanente — refactor migration 011)
INSERT INTO ot_incentivos_puesto (puesto_id, monto, concepto, activo) VALUES
((SELECT id FROM ot_puestos WHERE codigo='P001'), 4320.00, 'Incentivo nocturno Naco', 1),
((SELECT id FROM ot_puestos WHERE codigo='P002'), 5400.00, 'Incentivo bóveda', 1),
((SELECT id FROM ot_puestos WHERE codigo='P003'), 3600.00, 'Incentivo Piantini', 1),
((SELECT id FROM ot_puestos WHERE codigo='P004'), 3960.00, 'Incentivo parqueo', 1);

-- 7. Turnos (mayo 2026) — empleados reales de rh_empleado
INSERT INTO ot_turnos (empleado_id, puesto_id, fecha, hora_entrada, hora_salida, horas_normales, horas_extras, tipo_turno, es_feriado, feriado_id, procesado_nomina) VALUES
(66,  (SELECT id FROM ot_puestos WHERE codigo='P001'), '2026-05-01', '06:00:00', '18:00:00', 10.00, 2.00, 'DIURNO',   1, (SELECT id FROM ot_feriados WHERE fecha='2026-05-01'), 0),
(74,  (SELECT id FROM ot_puestos WHERE codigo='P002'), '2026-05-01', '18:00:00', '06:00:00', 10.00, 2.00, 'NOCTURNO', 1, (SELECT id FROM ot_feriados WHERE fecha='2026-05-01'), 0),
(82,  (SELECT id FROM ot_puestos WHERE codigo='P003'), '2026-05-01', '07:00:00', '19:00:00', 10.00, 2.00, 'DIURNO',   1, (SELECT id FROM ot_feriados WHERE fecha='2026-05-01'), 0),
(66,  (SELECT id FROM ot_puestos WHERE codigo='P001'), '2026-05-02', '06:00:00', '18:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 0),
(91,  (SELECT id FROM ot_puestos WHERE codigo='P002'), '2026-05-02', '18:00:00', '06:00:00', 10.00, 2.00, 'NOCTURNO', 0, NULL, 0),
(82,  (SELECT id FROM ot_puestos WHERE codigo='P003'), '2026-05-02', '07:00:00', '19:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 0),
(95,  (SELECT id FROM ot_puestos WHERE codigo='P004'), '2026-05-02', '06:00:00', '14:00:00',  8.00, 0.00, 'DIURNO',   0, NULL, 0),
(74,  (SELECT id FROM ot_puestos WHERE codigo='P001'), '2026-05-03', '06:00:00', '18:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 0),
(91,  (SELECT id FROM ot_puestos WHERE codigo='P002'), '2026-05-03', '18:00:00', '06:00:00', 10.00, 2.00, 'NOCTURNO', 0, NULL, 0),
(101, (SELECT id FROM ot_puestos WHERE codigo='P003'), '2026-05-03', '07:00:00', '19:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 0),
(95,  (SELECT id FROM ot_puestos WHERE codigo='P004'), '2026-05-03', '06:00:00', '14:00:00',  8.00, 0.00, 'DIURNO',   0, NULL, 0),
(66,  (SELECT id FROM ot_puestos WHERE codigo='P001'), '2026-05-04', '06:00:00', '18:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 1),
(74,  (SELECT id FROM ot_puestos WHERE codigo='P002'), '2026-05-04', '18:00:00', '06:00:00', 10.00, 2.00, 'NOCTURNO', 0, NULL, 1),
(82,  (SELECT id FROM ot_puestos WHERE codigo='P003'), '2026-05-04', '07:00:00', '19:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 1),
(139, (SELECT id FROM ot_puestos WHERE codigo='P004'), '2026-05-04', '06:00:00', '14:00:00',  8.00, 0.00, 'DIURNO',   0, NULL, 1),
(91,  (SELECT id FROM ot_puestos WHERE codigo='P001'), '2026-05-05', '06:00:00', '18:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 1),
(74,  (SELECT id FROM ot_puestos WHERE codigo='P002'), '2026-05-05', '18:00:00', '06:00:00', 10.00, 2.00, 'NOCTURNO', 0, NULL, 1),
(101, (SELECT id FROM ot_puestos WHERE codigo='P003'), '2026-05-05', '07:00:00', '19:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 1),
(139, (SELECT id FROM ot_puestos WHERE codigo='P004'), '2026-05-05', '06:00:00', '14:00:00',  8.00, 0.00, 'DIURNO',   0, NULL, 1),
(66,  (SELECT id FROM ot_puestos WHERE codigo='P001'), '2026-05-06', '06:00:00', '18:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 1),
(91,  (SELECT id FROM ot_puestos WHERE codigo='P002'), '2026-05-06', '18:00:00', '06:00:00', 10.00, 2.00, 'NOCTURNO', 0, NULL, 1),
(82,  (SELECT id FROM ot_puestos WHERE codigo='P003'), '2026-05-07', '07:00:00', '19:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 1),
(95,  (SELECT id FROM ot_puestos WHERE codigo='P004'), '2026-05-07', '06:00:00', '14:00:00',  8.00, 0.00, 'DIURNO',   0, NULL, 1),
(74,  (SELECT id FROM ot_puestos WHERE codigo='P001'), '2026-05-08', '06:00:00', '18:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 1),
(91,  (SELECT id FROM ot_puestos WHERE codigo='P002'), '2026-05-08', '18:00:00', '06:00:00', 10.00, 2.00, 'NOCTURNO', 0, NULL, 1),
(101, (SELECT id FROM ot_puestos WHERE codigo='P003'), '2026-05-09', '07:00:00', '19:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 1),
(139, (SELECT id FROM ot_puestos WHERE codigo='P004'), '2026-05-09', '06:00:00', '14:00:00',  8.00, 0.00, 'DIURNO',   0, NULL, 1),
(66,  (SELECT id FROM ot_puestos WHERE codigo='P001'), '2026-05-12', '06:00:00', '18:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 0),
(74,  (SELECT id FROM ot_puestos WHERE codigo='P002'), '2026-05-12', '18:00:00', '06:00:00', 10.00, 2.00, 'NOCTURNO', 0, NULL, 0),
(82,  (SELECT id FROM ot_puestos WHERE codigo='P003'), '2026-05-13', '07:00:00', '19:00:00', 10.00, 2.00, 'DIURNO',   0, NULL, 0),
(95,  (SELECT id FROM ot_puestos WHERE codigo='P004'), '2026-05-13', '06:00:00', '14:00:00',  8.00, 0.00, 'DIURNO',   0, NULL, 0);

SELECT 'Seed completado' AS estado;
SELECT 'clientes' AS tabla, COUNT(*) AS n FROM ot_clientes
UNION ALL SELECT 'ubicaciones', COUNT(*) FROM ot_ubicaciones
UNION ALL SELECT 'puestos', COUNT(*) FROM ot_puestos
UNION ALL SELECT 'feriados', COUNT(*) FROM ot_feriados
UNION ALL SELECT 'incentivos_puesto', COUNT(*) FROM ot_incentivos_puesto
UNION ALL SELECT 'turnos', COUNT(*) FROM ot_turnos
UNION ALL SELECT 'configuracion_turnos', COUNT(*) FROM ot_configuracion_turnos
UNION ALL SELECT 'sys_usuarios', COUNT(*) FROM ot_sys_usuarios;
