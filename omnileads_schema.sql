--
-- PostgreSQL database dump
--

-- Dumped from database version 11.11
-- Dumped by pg_dump version 16.2

-- Started on 2025-10-22 15:13:42

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 7 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- TOC entry 1 (class 3079 OID 16386)
-- Name: plperl; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plperl WITH SCHEMA pg_catalog;


--
-- TOC entry 4835 (class 0 OID 0)
-- Dependencies: 1
-- Name: EXTENSION plperl; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plperl IS 'PL/Perl procedural language';


--
-- TOC entry 358 (class 1255 OID 18198)
-- Name: insert_queue_log_ominicontacto_queue_log(); Type: FUNCTION; Schema: public; Owner: omnileads
--

CREATE FUNCTION public.insert_queue_log_ominicontacto_queue_log() RETURNS trigger
    LANGUAGE plperl
    AS $_X$
$fecha = $_TD->{new}{time};
$callid = $_TD->{new}{callid};
$queuename = $_TD->{new}{queuename}; # <id-campana>-<tipo-campana>-<tipo-llamada>
$agente_id = $_TD->{new}{agent};
$event = $_TD->{new}{event};
# 'data1' en los logs de llamadas tiene el número marcado y en los eventos de agente
# el id de la pausa
$data1 = $_TD->{new}{data1};
$contacto_id = $_TD->{new}{data2};
$bridge_wait_time = $_TD->{new}{data3};
$duracion_llamada = $_TD->{new}{data4};
$archivo_grabacion = $_TD->{new}{data5};

@EVENTOS_AGENTE = ('ADDMEMBER', 'REMOVEMEMBER', 'PAUSEALL', 'UNPAUSEALL');

@EVENTOS_LLAMADAS = (
    'DIAL',
    'ANSWER',
    'CONNECT',
    'COMPLETEAGENT',
    'COMPLETEOUTNUM',
    'ENTERQUEUE',
    'EXITWITHTIMEOUT',
    'ABANDON',
    'NOANSWER',
    'CANCEL',
    'BUSY',
    'CHANUNAVAIL',
    'OTHER',
    'FAIL',
    'AMD',
    'BLACKLIST',
    'RINGNOANSWER',
    'NONDIALPLAN',
    'CONGESTION',
    'ABANDONWEL',
    );

@EVENTOS_TRANSFERENCIAS = (
    'BT-TRY',
    'BT-ANSWER',
    'BT-BUSY',
    'BT-CANCEL',
    'BT-CHANUNAVAIL',
    'BT-CONGESTION',
    'BT-ABANDON',
    'BT-NOANSWER',
    'CAMPT-TRY',
    'CAMPT-FAIL',
    'CAMPT-COMPLETE',
    'ENTERQUEUE-TRANSFER',
    'CT-TRY',
    'CT-ANSWER',
    'CT-ACCEPT',
    'CT-COMPLETE',
    'CT-DISCARD',
    'CT-BUSY',
    'CT-CANCEL',
    'CT-CHANUNAVAIL',
    'CT-CONGESTION',
    'BTOUT-TRY',
    'BTOUT-ANSWER',
    'BTOUT-BUSY',
    'BTOUT-CANCEL',
    'BTOUT-CONGESTION',
    'BTOUT-CHANUNAVAIL',
    'BTOUT-ABANDON',
    'BTOUT-NONDIALPLAN',
    'CTOUT-TRY',
    'CTOUT-ANSWER',
    'CTOUT-ACCEPT',
    'CTOUT-COMPLETE',
    'CTOUT-DISCARD',
    'CTOUT-BUSY',
    'CTOUT-CANCEL',
    'CTOUT-CHANUNAVAIL',
    'CTOUT-CONGESTION',
    'CTOUT-NONDIALPLAN',
    'COMPLETE-CTOUT',
    'COMPLETE-CT',
    'COMPLETE-BT',
    'COMPLETE-BTOUT',
    'COMPLETE-CAMPT',
    'CT-ABANDON',
    'ABANDON-CT',
    'CTOUT-ABANDON',
    'ABANDON-CTOUT',
    );

@EVENTOS = (@EVENTOS_LLAMADAS, @EVENTOS_TRANSFERENCIAS);


sub is_number  {
    if (length($_[0]) == length(int($_[0]))) {
        return 1;
    }
    else {
        return 0;
    }
}


sub procesar_datos_transferencias {
    # Parsea la información de los valores generados desde los campos 'agent', 'data4' y
    # 'data5' para obtener los valores de los campos de los logs de transferencias de llamadas:
    # (agente_extra_id, campana_extra_id, numero_extra)
    $agente_data = $_TD->{new}{agent};
    ($agente_id_modificado, $agente_extra_id, $campana_extra_id, $numero_extra) = (-1, -1, -1, -1);
    eval {
        ($valor_transf_1, $valor_transf_2) = split("-", $agente_data);
    }
    or do {
        ($valor_transf_1, $valor_transf_2) = ($agente_data, undef);
    };
    if( grep $_ eq $event,  ('BT-TRY', 'CAMPT-COMPLETE', 'CT-TRY')) {
        # agente_id_origen - id_agente_origen
        $agente_id_modificado = $valor_transf_1;
        $agente_extra_id = $valor_transf_2;
    }
    elsif ( $event eq 'CAMPT-TRY') {
        # agente_id - id_camp_destino
        $agente_id_modificado = $valor_transf_1;
        $campana_extra_id = $valor_transf_2;
    }
    elsif ( $event eq 'ENTERQUEUE-TRANSFER') {
        # id_camp_origen - id_agente_origen (en data4, data5)
        $campana_extra_id = $_TD->{new}{data4};
        $agente_id_modificado = $_TD->{new}{data5};
    }
    elsif ($event eq ('BTOUT-TRY', 'CTOUT-TRY')) {
        # agente_id_origen - nro_telefono_destino
        $agente_id_modificado = $valor_transf_1;
        $numero_extra = $valor_transf_2;
    }
    elsif ( grep $_ eq $event,  ('BTOUT-ANSWER', 'BTOUT-BUSY', 'BTOUT-CANCEL', 'BTOUT-CONGESTION',
                                 'BTOUT-CHANUNAVAIL', 'BTOUT-ABANDON', 'CTOUT-ANSWER', 'CTOUT-ACCEPT',
                                 'CTOUT-DISCARD', 'CTOUT-BUSY', 'CTOUT-CANCEL', 'CTOUT-CHANUNAVAIL',
                                 'CTOUT-CONGESTION', 'COMPLETE-BTOUT', 'COMPLETE-CTOUT',
                                 'CTOUT-ABANDON', 'BTOUT-NONDIALPLAN', 'CTOUT-NONDIALPLAN')) {
        # el valor del campo 'agent' tiene un número de telefono
        $agente_id_modificado = -1;
        $numero_extra = $valor_transf_1;
    }
    else {
        # en los eventos de transferencias con un solo valor que contiene el id de un agente
        # solo se mantiene el valor de 'agente_id'
        $agente_id_modificado = $valor_transf_1;
    }
    return ($agente_id_modificado, $agente_extra_id, $campana_extra_id, $numero_extra);
}

if( grep $_ eq $event,  @EVENTOS_AGENTE) { # TODO: ver como usar 'and' con 'grep' en Perl
    if ($queuename == 'ALL') {
        # es un log de la actividad de un agente
        $_SHARED{plan_agente_log} = spi_prepare('INSERT INTO reportes_app_actividadagentelog( time, agente_id, event, pausa_id )VALUES( $1 ,$2, $3, $4 )', 'TIMESTAMP WITH TIME ZONE', 'INTEGER', 'TEXT', 'TEXT');
        if ( is_number($agente_id) == 1 || $agente_id == -1) {
            eval {
                spi_exec_prepared($_SHARED{plan_agente_log}, {limit => 1}, $fecha, $agente_id, $event, $data1);
            }
            or do {
                my $e = $@;
                my $entrada = "time=$fecha,\nagente_id=$agente_id,\nevent=$event,\ndata1=$data1,\n";
                elog(ERROR, "Error $e trying to insert input $entrada");
            };
        }

    }
}

elsif ( grep $_ eq $event,  @EVENTOS)  {
    eval {
        ($campana_id, $tipo_campana, $tipo_llamada) = split("-", $queuename);
    }
    or do {
        ($campana_id, $tipo_campana, $tipo_llamada) = (-1, -1, -1);
    };

    if (grep $_ eq $event,  @EVENTOS_TRANSFERENCIAS) {
        ($agente_id, $agente_extra_id, $campana_extra_id, $numero_extra) = procesar_datos_transferencias();
    } else {
        ($agente_extra_id, $campana_extra_id, $numero_extra) = (-1, -1, -1);
    }

    my $plan_llamadas_log =  spi_prepare('INSERT INTO reportes_app_llamadalog( time, callid, campana_id, tipo_campana, tipo_llamada, agente_id, event, numero_marcado, contacto_id, bridge_wait_time, duracion_llamada, archivo_grabacion, agente_extra_id, campana_extra_id, numero_extra )VALUES( $1 ,$2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15 )',
                                         'timestamp with time zone', 'text', 'int', 'int', 'int', 'int', 'text', 'text', 'int',
                                         'int', 'int', 'text', 'int', 'int', 'text');
    if (is_number($agente_id) == 1 || $agente_id == -1) {
        eval {
            spi_exec_prepared($plan_llamadas_log, {limit => 1}, $fecha, $callid, $campana_id, $tipo_campana, $tipo_llamada,
                              $agente_id, $event, $data1, $contacto_id, $bridge_wait_time,
                              $duracion_llamada, $archivo_grabacion, $agente_extra_id,
                              $campana_extra_id, $numero_extra);
        }
        or do {
            my $e = $@;
            my $entrada = "fecha=$fecha,\ncallid=$callid,\ncampana_id=$campana_id,\ntipo_campana=$tipo_campana,\n".
                "tipo_llamada=$tipo_llamada,\nagente_id=$agente_id,\nevent=$event,\ndata1=$data1,\n".
                "contacto_id=$contacto_id,\nbridge_wait_time=$bridge_wait_time,\nduracion_llamada=$duracion_llamada,\n".
                "archivo_grabacion=$archivo_grabacion,\nagente_extra_id=$agente_extra_id,\ncampana_extra_id=$campana_extra_id,\n".
                "numero_extra=$numero_extra.\n";
            elog(ERROR, "Error $e trying to insert input $entrada");
        };
    }

}

else {
    # no insertamos logs de estos eventos de momento
}

return;

$_X$;


ALTER FUNCTION public.insert_queue_log_ominicontacto_queue_log() OWNER TO omnileads;

SET default_tablespace = '';

--
-- TOC entry 204 (class 1259 OID 16422)
-- Name: auth_group; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO omnileads;

--
-- TOC entry 203 (class 1259 OID 16420)
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.auth_group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.auth_group_id_seq OWNER TO omnileads;

--
-- TOC entry 4837 (class 0 OID 0)
-- Dependencies: 203
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;


--
-- TOC entry 206 (class 1259 OID 16432)
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO omnileads;

--
-- TOC entry 205 (class 1259 OID 16430)
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.auth_group_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.auth_group_permissions_id_seq OWNER TO omnileads;

--
-- TOC entry 4839 (class 0 OID 0)
-- Dependencies: 205
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.auth_group_permissions_id_seq OWNED BY public.auth_group_permissions.id;


--
-- TOC entry 202 (class 1259 OID 16414)
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO omnileads;

--
-- TOC entry 201 (class 1259 OID 16412)
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.auth_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.auth_permission_id_seq OWNER TO omnileads;

--
-- TOC entry 4841 (class 0 OID 0)
-- Dependencies: 201
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;


--
-- TOC entry 268 (class 1259 OID 17214)
-- Name: authtoken_token; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.authtoken_token (
    key character varying(40) NOT NULL,
    created timestamp with time zone NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.authtoken_token OWNER TO omnileads;

--
-- TOC entry 304 (class 1259 OID 17612)
-- Name: configuracion_telefonia_app_amdconf; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_amdconf (
    id integer NOT NULL,
    initial_silence integer NOT NULL,
    greeting integer NOT NULL,
    after_greeting_silence integer NOT NULL,
    total_analysis_time integer NOT NULL,
    min_word_length integer NOT NULL,
    between_words_silence integer NOT NULL,
    maximum_number_of_words integer NOT NULL,
    maximum_word_length integer NOT NULL,
    silence_threshold integer NOT NULL,
    CONSTRAINT configuracion_telefonia_app_amdco_maximum_number_of_words_check CHECK ((maximum_number_of_words >= 0)),
    CONSTRAINT configuracion_telefonia_app_amdcon_after_greeting_silence_check CHECK ((after_greeting_silence >= 0)),
    CONSTRAINT configuracion_telefonia_app_amdconf_between_words_silence_check CHECK ((between_words_silence >= 0)),
    CONSTRAINT configuracion_telefonia_app_amdconf_greeting_check CHECK ((greeting >= 0)),
    CONSTRAINT configuracion_telefonia_app_amdconf_initial_silence_check CHECK ((initial_silence >= 0)),
    CONSTRAINT configuracion_telefonia_app_amdconf_maximum_word_length_check CHECK ((maximum_word_length >= 0)),
    CONSTRAINT configuracion_telefonia_app_amdconf_min_word_length_check CHECK ((min_word_length >= 0)),
    CONSTRAINT configuracion_telefonia_app_amdconf_silence_threshold_check CHECK ((silence_threshold >= 0)),
    CONSTRAINT configuracion_telefonia_app_amdconf_total_analysis_time_check CHECK ((total_analysis_time >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_amdconf OWNER TO omnileads;

--
-- TOC entry 303 (class 1259 OID 17610)
-- Name: configuracion_telefonia_app_amdconf_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_amdconf_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_amdconf_id_seq OWNER TO omnileads;

--
-- TOC entry 4844 (class 0 OID 0)
-- Dependencies: 303
-- Name: configuracion_telefonia_app_amdconf_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_amdconf_id_seq OWNED BY public.configuracion_telefonia_app_amdconf.id;


--
-- TOC entry 308 (class 1259 OID 17637)
-- Name: configuracion_telefonia_app_audiosasteriskconf; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_audiosasteriskconf (
    id integer NOT NULL,
    paquete_idioma character varying(2) NOT NULL,
    esta_instalado boolean NOT NULL
);


ALTER TABLE public.configuracion_telefonia_app_audiosasteriskconf OWNER TO omnileads;

--
-- TOC entry 307 (class 1259 OID 17635)
-- Name: configuracion_telefonia_app_audiosasteriskconf_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_audiosasteriskconf_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_audiosasteriskconf_id_seq OWNER TO omnileads;

--
-- TOC entry 4846 (class 0 OID 0)
-- Dependencies: 307
-- Name: configuracion_telefonia_app_audiosasteriskconf_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_audiosasteriskconf_id_seq OWNED BY public.configuracion_telefonia_app_audiosasteriskconf.id;


--
-- TOC entry 270 (class 1259 OID 17241)
-- Name: configuracion_telefonia_app_destinoentrante; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_destinoentrante (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL,
    tipo integer NOT NULL,
    object_id integer NOT NULL,
    content_type_id integer NOT NULL,
    CONSTRAINT configuracion_telefonia_app_destinoentrante_object_id_check CHECK ((object_id >= 0)),
    CONSTRAINT configuracion_telefonia_app_destinoentrante_tipo_check CHECK ((tipo >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_destinoentrante OWNER TO omnileads;

--
-- TOC entry 269 (class 1259 OID 17239)
-- Name: configuracion_telefonia_app_destinoentrante_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_destinoentrante_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_destinoentrante_id_seq OWNER TO omnileads;

--
-- TOC entry 4848 (class 0 OID 0)
-- Dependencies: 269
-- Name: configuracion_telefonia_app_destinoentrante_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_destinoentrante_id_seq OWNED BY public.configuracion_telefonia_app_destinoentrante.id;


--
-- TOC entry 298 (class 1259 OID 17568)
-- Name: configuracion_telefonia_app_destinopersonalizado; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_destinopersonalizado (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL,
    custom_destination character varying(50) NOT NULL
);


ALTER TABLE public.configuracion_telefonia_app_destinopersonalizado OWNER TO omnileads;

--
-- TOC entry 297 (class 1259 OID 17566)
-- Name: configuracion_telefonia_app_destinopersonalizado_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_destinopersonalizado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_destinopersonalizado_id_seq OWNER TO omnileads;

--
-- TOC entry 4850 (class 0 OID 0)
-- Dependencies: 297
-- Name: configuracion_telefonia_app_destinopersonalizado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_destinopersonalizado_id_seq OWNED BY public.configuracion_telefonia_app_destinopersonalizado.id;


--
-- TOC entry 306 (class 1259 OID 17629)
-- Name: configuracion_telefonia_app_esquemagrabaciones; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_esquemagrabaciones (
    id integer NOT NULL,
    id_contacto boolean NOT NULL,
    fecha boolean NOT NULL,
    telefono_contacto boolean NOT NULL,
    id_campana boolean NOT NULL,
    id_externo_contacto boolean NOT NULL,
    id_externo_campana boolean NOT NULL,
    id_agente boolean NOT NULL
);


ALTER TABLE public.configuracion_telefonia_app_esquemagrabaciones OWNER TO omnileads;

--
-- TOC entry 305 (class 1259 OID 17627)
-- Name: configuracion_telefonia_app_esquemagrabaciones_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_esquemagrabaciones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_esquemagrabaciones_id_seq OWNER TO omnileads;

--
-- TOC entry 4852 (class 0 OID 0)
-- Dependencies: 305
-- Name: configuracion_telefonia_app_esquemagrabaciones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_esquemagrabaciones_id_seq OWNED BY public.configuracion_telefonia_app_esquemagrabaciones.id;


--
-- TOC entry 272 (class 1259 OID 17253)
-- Name: configuracion_telefonia_app_grupohorario; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_grupohorario (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL
);


ALTER TABLE public.configuracion_telefonia_app_grupohorario OWNER TO omnileads;

--
-- TOC entry 271 (class 1259 OID 17251)
-- Name: configuracion_telefonia_app_grupohorario_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_grupohorario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_grupohorario_id_seq OWNER TO omnileads;

--
-- TOC entry 4854 (class 0 OID 0)
-- Dependencies: 271
-- Name: configuracion_telefonia_app_grupohorario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_grupohorario_id_seq OWNED BY public.configuracion_telefonia_app_grupohorario.id;


--
-- TOC entry 292 (class 1259 OID 17453)
-- Name: configuracion_telefonia_app_hangup; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_hangup (
    id integer NOT NULL
);


ALTER TABLE public.configuracion_telefonia_app_hangup OWNER TO omnileads;

--
-- TOC entry 291 (class 1259 OID 17451)
-- Name: configuracion_telefonia_app_hangup_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_hangup_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_hangup_id_seq OWNER TO omnileads;

--
-- TOC entry 4856 (class 0 OID 0)
-- Dependencies: 291
-- Name: configuracion_telefonia_app_hangup_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_hangup_id_seq OWNED BY public.configuracion_telefonia_app_hangup.id;


--
-- TOC entry 296 (class 1259 OID 17545)
-- Name: configuracion_telefonia_app_identificadorcliente; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_identificadorcliente (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL,
    tipo_interaccion integer NOT NULL,
    url character varying(128),
    longitud_id_esperado integer,
    timeout integer NOT NULL,
    intentos integer NOT NULL,
    audio_id integer NOT NULL,
    CONSTRAINT configuracion_telefonia_app_identifi_longitud_id_esperado_check CHECK ((longitud_id_esperado >= 0)),
    CONSTRAINT configuracion_telefonia_app_identificado_tipo_interaccion_check CHECK ((tipo_interaccion >= 0)),
    CONSTRAINT configuracion_telefonia_app_identificadorcliente_intentos_check CHECK ((intentos >= 0)),
    CONSTRAINT configuracion_telefonia_app_identificadorcliente_timeout_check CHECK ((timeout >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_identificadorcliente OWNER TO omnileads;

--
-- TOC entry 295 (class 1259 OID 17543)
-- Name: configuracion_telefonia_app_identificadorcliente_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_identificadorcliente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_identificadorcliente_id_seq OWNER TO omnileads;

--
-- TOC entry 4858 (class 0 OID 0)
-- Dependencies: 295
-- Name: configuracion_telefonia_app_identificadorcliente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_identificadorcliente_id_seq OWNED BY public.configuracion_telefonia_app_identificadorcliente.id;


--
-- TOC entry 274 (class 1259 OID 17263)
-- Name: configuracion_telefonia_app_ivr; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_ivr (
    id integer NOT NULL,
    nombre character varying(30) NOT NULL,
    descripcion character varying(30) NOT NULL,
    time_out integer NOT NULL,
    time_out_retries integer NOT NULL,
    invalid_retries integer NOT NULL,
    audio_principal_id integer NOT NULL,
    invalid_audio_id integer,
    time_out_audio_id integer,
    CONSTRAINT configuracion_telefonia_app_ivr_invalid_retries_check CHECK ((invalid_retries >= 0)),
    CONSTRAINT configuracion_telefonia_app_ivr_time_out_check CHECK ((time_out >= 0)),
    CONSTRAINT configuracion_telefonia_app_ivr_time_out_retries_check CHECK ((time_out_retries >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_ivr OWNER TO omnileads;

--
-- TOC entry 273 (class 1259 OID 17261)
-- Name: configuracion_telefonia_app_ivr_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_ivr_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_ivr_id_seq OWNER TO omnileads;

--
-- TOC entry 4860 (class 0 OID 0)
-- Dependencies: 273
-- Name: configuracion_telefonia_app_ivr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_ivr_id_seq OWNED BY public.configuracion_telefonia_app_ivr.id;


--
-- TOC entry 300 (class 1259 OID 17584)
-- Name: configuracion_telefonia_app_musicadeespera; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_musicadeespera (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    audio_original character varying(100),
    audio_asterisk character varying(100),
    playlist_id integer NOT NULL
);


ALTER TABLE public.configuracion_telefonia_app_musicadeespera OWNER TO omnileads;

--
-- TOC entry 299 (class 1259 OID 17582)
-- Name: configuracion_telefonia_app_musicadeespera_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_musicadeespera_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_musicadeespera_id_seq OWNER TO omnileads;

--
-- TOC entry 4862 (class 0 OID 0)
-- Dependencies: 299
-- Name: configuracion_telefonia_app_musicadeespera_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_musicadeespera_id_seq OWNED BY public.configuracion_telefonia_app_musicadeespera.id;


--
-- TOC entry 276 (class 1259 OID 17276)
-- Name: configuracion_telefonia_app_opciondestino; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_opciondestino (
    id integer NOT NULL,
    valor character varying(30) NOT NULL,
    destino_anterior_id integer NOT NULL,
    destino_siguiente_id integer NOT NULL
);


ALTER TABLE public.configuracion_telefonia_app_opciondestino OWNER TO omnileads;

--
-- TOC entry 275 (class 1259 OID 17274)
-- Name: configuracion_telefonia_app_opciondestino_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_opciondestino_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_opciondestino_id_seq OWNER TO omnileads;

--
-- TOC entry 4864 (class 0 OID 0)
-- Dependencies: 275
-- Name: configuracion_telefonia_app_opciondestino_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_opciondestino_id_seq OWNED BY public.configuracion_telefonia_app_opciondestino.id;


--
-- TOC entry 278 (class 1259 OID 17284)
-- Name: configuracion_telefonia_app_ordentroncal; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_ordentroncal (
    id integer NOT NULL,
    orden integer NOT NULL,
    ruta_saliente_id integer NOT NULL,
    troncal_id integer NOT NULL,
    CONSTRAINT configuracion_telefonia_app_ordentroncal_orden_check CHECK ((orden >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_ordentroncal OWNER TO omnileads;

--
-- TOC entry 277 (class 1259 OID 17282)
-- Name: configuracion_telefonia_app_ordentroncal_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_ordentroncal_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_ordentroncal_id_seq OWNER TO omnileads;

--
-- TOC entry 4866 (class 0 OID 0)
-- Dependencies: 277
-- Name: configuracion_telefonia_app_ordentroncal_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_ordentroncal_id_seq OWNED BY public.configuracion_telefonia_app_ordentroncal.id;


--
-- TOC entry 280 (class 1259 OID 17293)
-- Name: configuracion_telefonia_app_patrondediscado; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_patrondediscado (
    id integer NOT NULL,
    prepend character varying(32),
    prefix character varying(32),
    match_pattern character varying(100) NOT NULL,
    orden integer NOT NULL,
    ruta_saliente_id integer NOT NULL,
    CONSTRAINT configuracion_telefonia_app_patrondediscado_orden_check CHECK ((orden >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_patrondediscado OWNER TO omnileads;

--
-- TOC entry 279 (class 1259 OID 17291)
-- Name: configuracion_telefonia_app_patrondediscado_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_patrondediscado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_patrondediscado_id_seq OWNER TO omnileads;

--
-- TOC entry 4868 (class 0 OID 0)
-- Dependencies: 279
-- Name: configuracion_telefonia_app_patrondediscado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_patrondediscado_id_seq OWNED BY public.configuracion_telefonia_app_patrondediscado.id;


--
-- TOC entry 302 (class 1259 OID 17594)
-- Name: configuracion_telefonia_app_playlist; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_playlist (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL
);


ALTER TABLE public.configuracion_telefonia_app_playlist OWNER TO omnileads;

--
-- TOC entry 301 (class 1259 OID 17592)
-- Name: configuracion_telefonia_app_playlist_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_playlist_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_playlist_id_seq OWNER TO omnileads;

--
-- TOC entry 4870 (class 0 OID 0)
-- Dependencies: 301
-- Name: configuracion_telefonia_app_playlist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_playlist_id_seq OWNED BY public.configuracion_telefonia_app_playlist.id;


--
-- TOC entry 282 (class 1259 OID 17302)
-- Name: configuracion_telefonia_app_rutaentrante; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_rutaentrante (
    id integer NOT NULL,
    nombre character varying(30) NOT NULL,
    telefono character varying(30) NOT NULL,
    prefijo_caller_id character varying(30),
    idioma integer NOT NULL,
    destino_id integer NOT NULL,
    CONSTRAINT configuracion_telefonia_app_rutaentrante_idioma_check CHECK ((idioma >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_rutaentrante OWNER TO omnileads;

--
-- TOC entry 281 (class 1259 OID 17300)
-- Name: configuracion_telefonia_app_rutaentrante_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_rutaentrante_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_rutaentrante_id_seq OWNER TO omnileads;

--
-- TOC entry 4872 (class 0 OID 0)
-- Dependencies: 281
-- Name: configuracion_telefonia_app_rutaentrante_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_rutaentrante_id_seq OWNED BY public.configuracion_telefonia_app_rutaentrante.id;


--
-- TOC entry 284 (class 1259 OID 17315)
-- Name: configuracion_telefonia_app_rutasaliente; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_rutasaliente (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL,
    ring_time integer NOT NULL,
    dial_options character varying(512) NOT NULL,
    orden integer NOT NULL,
    CONSTRAINT configuracion_telefonia_app_rutasaliente_orden_check CHECK ((orden >= 0)),
    CONSTRAINT configuracion_telefonia_app_rutasaliente_ring_time_check CHECK ((ring_time >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_rutasaliente OWNER TO omnileads;

--
-- TOC entry 283 (class 1259 OID 17313)
-- Name: configuracion_telefonia_app_rutasaliente_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_rutasaliente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_rutasaliente_id_seq OWNER TO omnileads;

--
-- TOC entry 4874 (class 0 OID 0)
-- Dependencies: 283
-- Name: configuracion_telefonia_app_rutasaliente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_rutasaliente_id_seq OWNED BY public.configuracion_telefonia_app_rutasaliente.id;


--
-- TOC entry 286 (class 1259 OID 17329)
-- Name: configuracion_telefonia_app_troncalsip; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_troncalsip (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL,
    canales_maximos integer NOT NULL,
    caller_id character varying(100),
    register_string character varying(100),
    text_config text NOT NULL,
    tecnologia integer NOT NULL,
    CONSTRAINT configuracion_telefonia_app_troncalsip_canales_maximos_check CHECK ((canales_maximos >= 0)),
    CONSTRAINT configuracion_telefonia_app_troncalsip_tecnologia_check CHECK ((tecnologia >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_troncalsip OWNER TO omnileads;

--
-- TOC entry 285 (class 1259 OID 17327)
-- Name: configuracion_telefonia_app_troncalsip_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_troncalsip_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_troncalsip_id_seq OWNER TO omnileads;

--
-- TOC entry 4876 (class 0 OID 0)
-- Dependencies: 285
-- Name: configuracion_telefonia_app_troncalsip_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_troncalsip_id_seq OWNED BY public.configuracion_telefonia_app_troncalsip.id;


--
-- TOC entry 288 (class 1259 OID 17343)
-- Name: configuracion_telefonia_app_validacionfechahora; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_validacionfechahora (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL,
    grupo_horario_id integer NOT NULL
);


ALTER TABLE public.configuracion_telefonia_app_validacionfechahora OWNER TO omnileads;

--
-- TOC entry 287 (class 1259 OID 17341)
-- Name: configuracion_telefonia_app_validacionfechahora_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_validacionfechahora_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_validacionfechahora_id_seq OWNER TO omnileads;

--
-- TOC entry 4878 (class 0 OID 0)
-- Dependencies: 287
-- Name: configuracion_telefonia_app_validacionfechahora_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_validacionfechahora_id_seq OWNED BY public.configuracion_telefonia_app_validacionfechahora.id;


--
-- TOC entry 290 (class 1259 OID 17353)
-- Name: configuracion_telefonia_app_validaciontiempo; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.configuracion_telefonia_app_validaciontiempo (
    id integer NOT NULL,
    tiempo_inicial time without time zone NOT NULL,
    tiempo_final time without time zone NOT NULL,
    dia_semana_inicial integer,
    dia_semana_final integer,
    dia_mes_inicio integer,
    dia_mes_final integer,
    mes_inicio integer,
    mes_final integer,
    grupo_horario_id integer NOT NULL,
    CONSTRAINT configuracion_telefonia_app_validacion_dia_semana_inicial_check CHECK ((dia_semana_inicial >= 0)),
    CONSTRAINT configuracion_telefonia_app_validacionti_dia_semana_final_check CHECK ((dia_semana_final >= 0)),
    CONSTRAINT configuracion_telefonia_app_validaciontiem_dia_mes_inicio_check CHECK ((dia_mes_inicio >= 0)),
    CONSTRAINT configuracion_telefonia_app_validaciontiemp_dia_mes_final_check CHECK ((dia_mes_final >= 0)),
    CONSTRAINT configuracion_telefonia_app_validaciontiempo_mes_final_check CHECK ((mes_final >= 0)),
    CONSTRAINT configuracion_telefonia_app_validaciontiempo_mes_inicio_check CHECK ((mes_inicio >= 0))
);


ALTER TABLE public.configuracion_telefonia_app_validaciontiempo OWNER TO omnileads;

--
-- TOC entry 289 (class 1259 OID 17351)
-- Name: configuracion_telefonia_app_validaciontiempo_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.configuracion_telefonia_app_validaciontiempo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuracion_telefonia_app_validaciontiempo_id_seq OWNER TO omnileads;

--
-- TOC entry 4880 (class 0 OID 0)
-- Dependencies: 289
-- Name: configuracion_telefonia_app_validaciontiempo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.configuracion_telefonia_app_validaciontiempo_id_seq OWNED BY public.configuracion_telefonia_app_validaciontiempo.id;


--
-- TOC entry 310 (class 1259 OID 17645)
-- Name: constance_config; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.constance_config (
    id integer NOT NULL,
    key character varying(255) NOT NULL,
    value text
);


ALTER TABLE public.constance_config OWNER TO omnileads;

--
-- TOC entry 309 (class 1259 OID 17643)
-- Name: constance_config_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.constance_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.constance_config_id_seq OWNER TO omnileads;

--
-- TOC entry 4882 (class 0 OID 0)
-- Dependencies: 309
-- Name: constance_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.constance_config_id_seq OWNED BY public.constance_config.id;


--
-- TOC entry 312 (class 1259 OID 17659)
-- Name: defender_accessattempt; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.defender_accessattempt (
    id integer NOT NULL,
    user_agent character varying(255) NOT NULL,
    ip_address inet,
    username character varying(255),
    http_accept character varying(1025) NOT NULL,
    path_info character varying(255) NOT NULL,
    attempt_time timestamp with time zone NOT NULL,
    login_valid boolean NOT NULL
);


ALTER TABLE public.defender_accessattempt OWNER TO omnileads;

--
-- TOC entry 311 (class 1259 OID 17657)
-- Name: defender_accessattempt_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.defender_accessattempt_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.defender_accessattempt_id_seq OWNER TO omnileads;

--
-- TOC entry 4884 (class 0 OID 0)
-- Dependencies: 311
-- Name: defender_accessattempt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.defender_accessattempt_id_seq OWNED BY public.defender_accessattempt.id;


--
-- TOC entry 267 (class 1259 OID 17192)
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO omnileads;

--
-- TOC entry 266 (class 1259 OID 17190)
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.django_admin_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.django_admin_log_id_seq OWNER TO omnileads;

--
-- TOC entry 4886 (class 0 OID 0)
-- Dependencies: 266
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.django_admin_log_id_seq OWNED BY public.django_admin_log.id;


--
-- TOC entry 200 (class 1259 OID 16404)
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO omnileads;

--
-- TOC entry 199 (class 1259 OID 16402)
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.django_content_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.django_content_type_id_seq OWNER TO omnileads;

--
-- TOC entry 4888 (class 0 OID 0)
-- Dependencies: 199
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.django_content_type_id_seq OWNED BY public.django_content_type.id;


--
-- TOC entry 198 (class 1259 OID 16393)
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO omnileads;

--
-- TOC entry 197 (class 1259 OID 16391)
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.django_migrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.django_migrations_id_seq OWNER TO omnileads;

--
-- TOC entry 4890 (class 0 OID 0)
-- Dependencies: 197
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.django_migrations_id_seq OWNED BY public.django_migrations.id;


--
-- TOC entry 353 (class 1259 OID 18230)
-- Name: django_session; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO omnileads;

--
-- TOC entry 314 (class 1259 OID 17670)
-- Name: easyaudit_crudevent; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.easyaudit_crudevent (
    id integer NOT NULL,
    event_type smallint NOT NULL,
    object_id character varying(255) NOT NULL,
    object_repr text,
    object_json_repr text,
    datetime timestamp with time zone NOT NULL,
    content_type_id integer NOT NULL,
    user_id integer,
    user_pk_as_string character varying(255),
    changed_fields text
);


ALTER TABLE public.easyaudit_crudevent OWNER TO omnileads;

--
-- TOC entry 313 (class 1259 OID 17668)
-- Name: easyaudit_crudevent_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.easyaudit_crudevent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.easyaudit_crudevent_id_seq OWNER TO omnileads;

--
-- TOC entry 4893 (class 0 OID 0)
-- Dependencies: 313
-- Name: easyaudit_crudevent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.easyaudit_crudevent_id_seq OWNED BY public.easyaudit_crudevent.id;


--
-- TOC entry 316 (class 1259 OID 17681)
-- Name: easyaudit_loginevent; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.easyaudit_loginevent (
    id integer NOT NULL,
    login_type smallint NOT NULL,
    username character varying(255),
    datetime timestamp with time zone NOT NULL,
    user_id integer,
    remote_ip character varying(50)
);


ALTER TABLE public.easyaudit_loginevent OWNER TO omnileads;

--
-- TOC entry 315 (class 1259 OID 17679)
-- Name: easyaudit_loginevent_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.easyaudit_loginevent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.easyaudit_loginevent_id_seq OWNER TO omnileads;

--
-- TOC entry 4895 (class 0 OID 0)
-- Dependencies: 315
-- Name: easyaudit_loginevent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.easyaudit_loginevent_id_seq OWNED BY public.easyaudit_loginevent.id;


--
-- TOC entry 318 (class 1259 OID 17718)
-- Name: easyaudit_requestevent; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.easyaudit_requestevent (
    id integer NOT NULL,
    url character varying(254) NOT NULL,
    method character varying(20) NOT NULL,
    query_string text,
    remote_ip character varying(50),
    datetime timestamp with time zone NOT NULL,
    user_id integer
);


ALTER TABLE public.easyaudit_requestevent OWNER TO omnileads;

--
-- TOC entry 317 (class 1259 OID 17716)
-- Name: easyaudit_requestevent_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.easyaudit_requestevent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.easyaudit_requestevent_id_seq OWNER TO omnileads;

--
-- TOC entry 4897 (class 0 OID 0)
-- Dependencies: 317
-- Name: easyaudit_requestevent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.easyaudit_requestevent_id_seq OWNED BY public.easyaudit_requestevent.id;


--
-- TOC entry 355 (class 1259 OID 18335)
-- Name: form_app_encuesta; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.form_app_encuesta (
    id integer NOT NULL,
    pregunta integer NOT NULL,
    respuesta integer NOT NULL,
    agente integer NOT NULL,
    unique_id character varying(30) NOT NULL,
    caller_id character varying(30) NOT NULL,
    fecha timestamp with time zone NOT NULL
);


ALTER TABLE public.form_app_encuesta OWNER TO omnileads;

--
-- TOC entry 354 (class 1259 OID 18333)
-- Name: form_app_encuesta_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.form_app_encuesta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.form_app_encuesta_id_seq OWNER TO omnileads;

--
-- TOC entry 4899 (class 0 OID 0)
-- Dependencies: 354
-- Name: form_app_encuesta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.form_app_encuesta_id_seq OWNED BY public.form_app_encuesta.id;


--
-- TOC entry 357 (class 1259 OID 18343)
-- Name: form_app_formulario; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.form_app_formulario (
    id integer NOT NULL,
    agente integer,
    nombre character varying(45) NOT NULL,
    matricula character varying(45) NOT NULL,
    contacto character varying(45) NOT NULL,
    correo character varying(254) NOT NULL,
    resultado integer,
    detalles integer,
    observaciones text NOT NULL,
    tipologia integer,
    tipo integer NOT NULL,
    fecha timestamp with time zone NOT NULL,
    caller_id character varying(45),
    campana_id integer
);


ALTER TABLE public.form_app_formulario OWNER TO omnileads;

--
-- TOC entry 356 (class 1259 OID 18341)
-- Name: form_app_formulario_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.form_app_formulario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.form_app_formulario_id_seq OWNER TO omnileads;

--
-- TOC entry 4901 (class 0 OID 0)
-- Dependencies: 356
-- Name: form_app_formulario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.form_app_formulario_id_seq OWNED BY public.form_app_formulario.id;


--
-- TOC entry 214 (class 1259 OID 16492)
-- Name: ominicontacto_app_actuacionvigente; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_actuacionvigente (
    id integer NOT NULL,
    domingo boolean NOT NULL,
    lunes boolean NOT NULL,
    martes boolean NOT NULL,
    miercoles boolean NOT NULL,
    jueves boolean NOT NULL,
    viernes boolean NOT NULL,
    sabado boolean NOT NULL,
    hora_desde time without time zone NOT NULL,
    hora_hasta time without time zone NOT NULL,
    campana_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_actuacionvigente OWNER TO omnileads;

--
-- TOC entry 213 (class 1259 OID 16490)
-- Name: ominicontacto_app_actuacionvigente_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_actuacionvigente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_actuacionvigente_id_seq OWNER TO omnileads;

--
-- TOC entry 4903 (class 0 OID 0)
-- Dependencies: 213
-- Name: ominicontacto_app_actuacionvigente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_actuacionvigente_id_seq OWNED BY public.ominicontacto_app_actuacionvigente.id;


--
-- TOC entry 216 (class 1259 OID 16512)
-- Name: ominicontacto_app_agendacontacto; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_agendacontacto (
    id integer NOT NULL,
    fecha date NOT NULL,
    hora time without time zone NOT NULL,
    tipo_agenda integer NOT NULL,
    observaciones text,
    agente_id integer NOT NULL,
    campana_id integer,
    contacto_id integer NOT NULL,
    CONSTRAINT ominicontacto_app_agendacontacto_tipo_agenda_check CHECK ((tipo_agenda >= 0))
);


ALTER TABLE public.ominicontacto_app_agendacontacto OWNER TO omnileads;

--
-- TOC entry 215 (class 1259 OID 16510)
-- Name: ominicontacto_app_agendacontacto_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_agendacontacto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_agendacontacto_id_seq OWNER TO omnileads;

--
-- TOC entry 4905 (class 0 OID 0)
-- Dependencies: 215
-- Name: ominicontacto_app_agendacontacto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_agendacontacto_id_seq OWNED BY public.ominicontacto_app_agendacontacto.id;


--
-- TOC entry 218 (class 1259 OID 16524)
-- Name: ominicontacto_app_agenteencontacto; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_agenteencontacto (
    id integer NOT NULL,
    agente_id integer NOT NULL,
    contacto_id integer NOT NULL,
    datos_contacto text NOT NULL,
    telefono_contacto character varying(128) NOT NULL,
    campana_id integer NOT NULL,
    estado integer NOT NULL,
    modificado timestamp with time zone,
    es_originario boolean NOT NULL,
    orden integer NOT NULL,
    CONSTRAINT ominicontacto_app_agenteencontacto_estado_check CHECK ((estado >= 0))
);


ALTER TABLE public.ominicontacto_app_agenteencontacto OWNER TO omnileads;

--
-- TOC entry 217 (class 1259 OID 16522)
-- Name: ominicontacto_app_agenteencontacto_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_agenteencontacto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_agenteencontacto_id_seq OWNER TO omnileads;

--
-- TOC entry 4907 (class 0 OID 0)
-- Dependencies: 217
-- Name: ominicontacto_app_agenteencontacto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_agenteencontacto_id_seq OWNED BY public.ominicontacto_app_agenteencontacto.id;


--
-- TOC entry 322 (class 1259 OID 17791)
-- Name: ominicontacto_app_agenteensistemaexterno; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_agenteensistemaexterno (
    id integer NOT NULL,
    id_externo_agente character varying(128) NOT NULL,
    agente_id integer NOT NULL,
    sistema_externo_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_agenteensistemaexterno OWNER TO omnileads;

--
-- TOC entry 321 (class 1259 OID 17789)
-- Name: ominicontacto_app_agenteensistemaexterno_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_agenteensistemaexterno_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_agenteensistemaexterno_id_seq OWNER TO omnileads;

--
-- TOC entry 4909 (class 0 OID 0)
-- Dependencies: 321
-- Name: ominicontacto_app_agenteensistemaexterno_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_agenteensistemaexterno_id_seq OWNED BY public.ominicontacto_app_agenteensistemaexterno.id;


--
-- TOC entry 220 (class 1259 OID 16536)
-- Name: ominicontacto_app_agenteprofile; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_agenteprofile (
    id integer NOT NULL,
    sip_extension integer NOT NULL,
    sip_password character varying(128),
    estado integer NOT NULL,
    is_inactive boolean NOT NULL,
    borrado boolean NOT NULL,
    grupo_id integer NOT NULL,
    reported_by_id integer NOT NULL,
    user_id integer NOT NULL,
    CONSTRAINT ominicontacto_app_agenteprofile_estado_check CHECK ((estado >= 0))
);


ALTER TABLE public.ominicontacto_app_agenteprofile OWNER TO omnileads;

--
-- TOC entry 219 (class 1259 OID 16534)
-- Name: ominicontacto_app_agenteprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_agenteprofile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_agenteprofile_id_seq OWNER TO omnileads;

--
-- TOC entry 4911 (class 0 OID 0)
-- Dependencies: 219
-- Name: ominicontacto_app_agenteprofile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_agenteprofile_id_seq OWNED BY public.ominicontacto_app_agenteprofile.id;


--
-- TOC entry 222 (class 1259 OID 16547)
-- Name: ominicontacto_app_archivodeaudio; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_archivodeaudio (
    id integer NOT NULL,
    descripcion character varying(100) NOT NULL,
    audio_original character varying(100),
    audio_asterisk character varying(100),
    borrado boolean NOT NULL
);


ALTER TABLE public.ominicontacto_app_archivodeaudio OWNER TO omnileads;

--
-- TOC entry 221 (class 1259 OID 16545)
-- Name: ominicontacto_app_archivodeaudio_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_archivodeaudio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_archivodeaudio_id_seq OWNER TO omnileads;

--
-- TOC entry 4913 (class 0 OID 0)
-- Dependencies: 221
-- Name: ominicontacto_app_archivodeaudio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_archivodeaudio_id_seq OWNED BY public.ominicontacto_app_archivodeaudio.id;


--
-- TOC entry 326 (class 1259 OID 17920)
-- Name: ominicontacto_app_auditoriacalificacion; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_auditoriacalificacion (
    id integer NOT NULL,
    resultado integer NOT NULL,
    observaciones text,
    calificacion_id integer NOT NULL,
    revisada boolean NOT NULL
);


ALTER TABLE public.ominicontacto_app_auditoriacalificacion OWNER TO omnileads;

--
-- TOC entry 325 (class 1259 OID 17918)
-- Name: ominicontacto_app_auditoriacalificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_auditoriacalificacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_auditoriacalificacion_id_seq OWNER TO omnileads;

--
-- TOC entry 4915 (class 0 OID 0)
-- Dependencies: 325
-- Name: ominicontacto_app_auditoriacalificacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_auditoriacalificacion_id_seq OWNED BY public.ominicontacto_app_auditoriacalificacion.id;


--
-- TOC entry 344 (class 1259 OID 18138)
-- Name: ominicontacto_app_autenticacionsitioexterno; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_autenticacionsitioexterno (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL,
    url character varying(250) NOT NULL,
    username character varying(128) NOT NULL,
    password character varying(128) NOT NULL,
    campo_token character varying(128) NOT NULL,
    duracion integer NOT NULL,
    campo_duracion character varying(128) NOT NULL,
    ssl_estricto boolean NOT NULL,
    token text,
    expiracion_token timestamp with time zone,
    CONSTRAINT ominicontacto_app_autenticacionsitioexterno_duracion_check CHECK ((duracion >= 0))
);


ALTER TABLE public.ominicontacto_app_autenticacionsitioexterno OWNER TO omnileads;

--
-- TOC entry 343 (class 1259 OID 18136)
-- Name: ominicontacto_app_autenticacionsitioexterno_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_autenticacionsitioexterno_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_autenticacionsitioexterno_id_seq OWNER TO omnileads;

--
-- TOC entry 4917 (class 0 OID 0)
-- Dependencies: 343
-- Name: ominicontacto_app_autenticacionsitioexterno_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_autenticacionsitioexterno_id_seq OWNED BY public.ominicontacto_app_autenticacionsitioexterno.id;


--
-- TOC entry 224 (class 1259 OID 16557)
-- Name: ominicontacto_app_blacklist; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_blacklist (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL,
    fecha_alta timestamp with time zone NOT NULL,
    archivo_importacion character varying(256) NOT NULL,
    nombre_archivo_importacion character varying(256) NOT NULL,
    sin_definir boolean NOT NULL,
    cantidad_contactos integer NOT NULL,
    fecha_modificacion timestamp with time zone NOT NULL,
    CONSTRAINT ominicontacto_app_backlist_cantidad_contactos_check CHECK ((cantidad_contactos >= 0))
);


ALTER TABLE public.ominicontacto_app_blacklist OWNER TO omnileads;

--
-- TOC entry 223 (class 1259 OID 16555)
-- Name: ominicontacto_app_backlist_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_backlist_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_backlist_id_seq OWNER TO omnileads;

--
-- TOC entry 4919 (class 0 OID 0)
-- Dependencies: 223
-- Name: ominicontacto_app_backlist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_backlist_id_seq OWNED BY public.ominicontacto_app_blacklist.id;


--
-- TOC entry 226 (class 1259 OID 16569)
-- Name: ominicontacto_app_basedatoscontacto; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_basedatoscontacto (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL,
    fecha_alta timestamp with time zone NOT NULL,
    archivo_importacion character varying(256) NOT NULL,
    nombre_archivo_importacion character varying(256) NOT NULL,
    metadata text,
    sin_definir boolean NOT NULL,
    cantidad_contactos integer NOT NULL,
    estado integer NOT NULL,
    oculto boolean NOT NULL,
    CONSTRAINT ominicontacto_app_basedatoscontacto_cantidad_contactos_check CHECK ((cantidad_contactos >= 0)),
    CONSTRAINT ominicontacto_app_basedatoscontacto_estado_check CHECK ((estado >= 0))
);


ALTER TABLE public.ominicontacto_app_basedatoscontacto OWNER TO omnileads;

--
-- TOC entry 225 (class 1259 OID 16567)
-- Name: ominicontacto_app_basedatoscontacto_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_basedatoscontacto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_basedatoscontacto_id_seq OWNER TO omnileads;

--
-- TOC entry 4921 (class 0 OID 0)
-- Dependencies: 225
-- Name: ominicontacto_app_basedatoscontacto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_basedatoscontacto_id_seq OWNED BY public.ominicontacto_app_basedatoscontacto.id;


--
-- TOC entry 228 (class 1259 OID 16582)
-- Name: ominicontacto_app_calificacioncliente; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_calificacioncliente (
    id integer NOT NULL,
    fecha timestamp with time zone NOT NULL,
    observaciones text,
    agendado boolean NOT NULL,
    es_calificacion_manual boolean NOT NULL,
    agente_id integer NOT NULL,
    contacto_id integer NOT NULL,
    opcion_calificacion_id integer NOT NULL,
    callid character varying(32),
    created timestamp with time zone NOT NULL,
    modified timestamp with time zone NOT NULL,
    tipo_agenda integer,
    CONSTRAINT ominicontacto_app_calificacioncliente_tipo_agenda_check CHECK ((tipo_agenda >= 0))
);


ALTER TABLE public.ominicontacto_app_calificacioncliente OWNER TO omnileads;

--
-- TOC entry 227 (class 1259 OID 16580)
-- Name: ominicontacto_app_calificacioncliente_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_calificacioncliente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_calificacioncliente_id_seq OWNER TO omnileads;

--
-- TOC entry 4923 (class 0 OID 0)
-- Dependencies: 227
-- Name: ominicontacto_app_calificacioncliente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_calificacioncliente_id_seq OWNED BY public.ominicontacto_app_calificacioncliente.id;


--
-- TOC entry 230 (class 1259 OID 16593)
-- Name: ominicontacto_app_campana; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_campana (
    id integer NOT NULL,
    estado integer NOT NULL,
    nombre character varying(128) NOT NULL,
    fecha_inicio date,
    fecha_fin date,
    oculto boolean NOT NULL,
    campaign_id_wombat integer,
    type integer NOT NULL,
    tipo_interaccion integer NOT NULL,
    es_template boolean NOT NULL,
    nombre_template character varying(128),
    es_manual boolean NOT NULL,
    objetivo integer NOT NULL,
    tiempo_desconexion integer NOT NULL,
    bd_contacto_id integer,
    reported_by_id integer NOT NULL,
    sitio_externo_id integer,
    mostrar_nombre boolean NOT NULL,
    id_externo character varying(128),
    sistema_externo_id integer,
    campo_desactivacion character varying(128),
    campos_bd_no_editables character varying(2052) NOT NULL,
    campos_bd_ocultos character varying(2052) NOT NULL,
    outcid character varying(128),
    outr_id integer,
    videocall_habilitada boolean NOT NULL,
    speech text,
    campo_direccion character varying(128),
    mostrar_did boolean NOT NULL,
    mostrar_nombre_ruta_entrante boolean NOT NULL,
    control_de_duplicados integer NOT NULL,
    prioridad integer NOT NULL,
    campos_bd_obligatorios character varying(2052) NOT NULL,
    CONSTRAINT ominicontacto_app_campana_control_de_duplicados_check CHECK ((control_de_duplicados >= 0)),
    CONSTRAINT ominicontacto_app_campana_estado_check CHECK ((estado >= 0)),
    CONSTRAINT ominicontacto_app_campana_objetivo_check CHECK ((objetivo >= 0)),
    CONSTRAINT ominicontacto_app_campana_prioridad_check CHECK ((prioridad >= 0)),
    CONSTRAINT ominicontacto_app_campana_tiempo_desconexion_check CHECK ((tiempo_desconexion >= 0)),
    CONSTRAINT ominicontacto_app_campana_tipo_interaccion_check CHECK ((tipo_interaccion >= 0)),
    CONSTRAINT ominicontacto_app_campana_type_check CHECK ((type >= 0))
);


ALTER TABLE public.ominicontacto_app_campana OWNER TO omnileads;

--
-- TOC entry 229 (class 1259 OID 16591)
-- Name: ominicontacto_app_campana_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_campana_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_campana_id_seq OWNER TO omnileads;

--
-- TOC entry 4925 (class 0 OID 0)
-- Dependencies: 229
-- Name: ominicontacto_app_campana_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_campana_id_seq OWNED BY public.ominicontacto_app_campana.id;


--
-- TOC entry 265 (class 1259 OID 16859)
-- Name: ominicontacto_app_campana_supervisors; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_campana_supervisors (
    id integer NOT NULL,
    campana_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_campana_supervisors OWNER TO omnileads;

--
-- TOC entry 264 (class 1259 OID 16857)
-- Name: ominicontacto_app_campana_supervisors_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_campana_supervisors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_campana_supervisors_id_seq OWNER TO omnileads;

--
-- TOC entry 4927 (class 0 OID 0)
-- Dependencies: 264
-- Name: ominicontacto_app_campana_supervisors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_campana_supervisors_id_seq OWNED BY public.ominicontacto_app_campana_supervisors.id;


--
-- TOC entry 232 (class 1259 OID 16608)
-- Name: ominicontacto_app_chat; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_chat (
    id integer NOT NULL,
    fecha_hora_chat timestamp with time zone NOT NULL,
    agente_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_chat OWNER TO omnileads;

--
-- TOC entry 231 (class 1259 OID 16606)
-- Name: ominicontacto_app_chat_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_chat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_chat_id_seq OWNER TO omnileads;

--
-- TOC entry 4929 (class 0 OID 0)
-- Dependencies: 231
-- Name: ominicontacto_app_chat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_chat_id_seq OWNED BY public.ominicontacto_app_chat.id;


--
-- TOC entry 324 (class 1259 OID 17836)
-- Name: ominicontacto_app_clientewebphoneprofile; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_clientewebphoneprofile (
    id integer NOT NULL,
    sip_extension integer NOT NULL,
    is_inactive boolean NOT NULL,
    borrado boolean NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_clientewebphoneprofile OWNER TO omnileads;

--
-- TOC entry 323 (class 1259 OID 17834)
-- Name: ominicontacto_app_clientewebphoneprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_clientewebphoneprofile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_clientewebphoneprofile_id_seq OWNER TO omnileads;

--
-- TOC entry 4931 (class 0 OID 0)
-- Dependencies: 323
-- Name: ominicontacto_app_clientewebphoneprofile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_clientewebphoneprofile_id_seq OWNED BY public.ominicontacto_app_clientewebphoneprofile.id;


--
-- TOC entry 332 (class 1259 OID 17992)
-- Name: ominicontacto_app_configuraciondeagentesdecampana; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_configuraciondeagentesdecampana (
    id integer NOT NULL,
    set_auto_attend_inbound boolean NOT NULL,
    auto_attend_inbound boolean NOT NULL,
    set_auto_attend_dialer boolean NOT NULL,
    auto_attend_dialer boolean NOT NULL,
    set_auto_unpause boolean NOT NULL,
    auto_unpause integer NOT NULL,
    set_obligar_calificacion boolean NOT NULL,
    obligar_calificacion boolean NOT NULL,
    campana_id integer NOT NULL,
    CONSTRAINT ominicontacto_app_configuraciondeagentesdeca_auto_unpause_check CHECK ((auto_unpause >= 0))
);


ALTER TABLE public.ominicontacto_app_configuraciondeagentesdecampana OWNER TO omnileads;

--
-- TOC entry 331 (class 1259 OID 17990)
-- Name: ominicontacto_app_configuraciondeagentesdecampana_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_configuraciondeagentesdecampana_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_configuraciondeagentesdecampana_id_seq OWNER TO omnileads;

--
-- TOC entry 4933 (class 0 OID 0)
-- Dependencies: 331
-- Name: ominicontacto_app_configuraciondeagentesdecampana_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_configuraciondeagentesdecampana_id_seq OWNED BY public.ominicontacto_app_configuraciondeagentesdecampana.id;


--
-- TOC entry 342 (class 1259 OID 18088)
-- Name: ominicontacto_app_configuraciondepausa; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_configuraciondepausa (
    id integer NOT NULL,
    time_to_end_pause integer NOT NULL,
    conjunto_de_pausa_id integer NOT NULL,
    pausa_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_configuraciondepausa OWNER TO omnileads;

--
-- TOC entry 341 (class 1259 OID 18086)
-- Name: ominicontacto_app_configuraciondepausa_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_configuraciondepausa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_configuraciondepausa_id_seq OWNER TO omnileads;

--
-- TOC entry 4935 (class 0 OID 0)
-- Dependencies: 341
-- Name: ominicontacto_app_configuraciondepausa_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_configuraciondepausa_id_seq OWNED BY public.ominicontacto_app_configuraciondepausa.id;


--
-- TOC entry 340 (class 1259 OID 18080)
-- Name: ominicontacto_app_conjuntodepausa; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_conjuntodepausa (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL
);


ALTER TABLE public.ominicontacto_app_conjuntodepausa OWNER TO omnileads;

--
-- TOC entry 339 (class 1259 OID 18078)
-- Name: ominicontacto_app_conjuntodepausa_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_conjuntodepausa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_conjuntodepausa_id_seq OWNER TO omnileads;

--
-- TOC entry 4937 (class 0 OID 0)
-- Dependencies: 339
-- Name: ominicontacto_app_conjuntodepausa_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_conjuntodepausa_id_seq OWNED BY public.ominicontacto_app_conjuntodepausa.id;


--
-- TOC entry 234 (class 1259 OID 16616)
-- Name: ominicontacto_app_contacto; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_contacto (
    id integer NOT NULL,
    telefono character varying(128) NOT NULL,
    datos text NOT NULL,
    bd_contacto_id integer,
    es_originario boolean NOT NULL,
    id_externo character varying(128)
);


ALTER TABLE public.ominicontacto_app_contacto OWNER TO omnileads;

--
-- TOC entry 233 (class 1259 OID 16614)
-- Name: ominicontacto_app_contacto_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_contacto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_contacto_id_seq OWNER TO omnileads;

--
-- TOC entry 4939 (class 0 OID 0)
-- Dependencies: 233
-- Name: ominicontacto_app_contacto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_contacto_id_seq OWNED BY public.ominicontacto_app_contacto.id;


--
-- TOC entry 328 (class 1259 OID 17944)
-- Name: ominicontacto_app_contactoblacklist; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_contactoblacklist (
    id integer NOT NULL,
    telefono character varying(128) NOT NULL,
    black_list_id integer
);


ALTER TABLE public.ominicontacto_app_contactoblacklist OWNER TO omnileads;

--
-- TOC entry 327 (class 1259 OID 17942)
-- Name: ominicontacto_app_contactoblacklist_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_contactoblacklist_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_contactoblacklist_id_seq OWNER TO omnileads;

--
-- TOC entry 4941 (class 0 OID 0)
-- Dependencies: 327
-- Name: ominicontacto_app_contactoblacklist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_contactoblacklist_id_seq OWNED BY public.ominicontacto_app_contactoblacklist.id;


--
-- TOC entry 338 (class 1259 OID 18042)
-- Name: ominicontacto_app_contactolistarapida; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_contactolistarapida (
    id integer NOT NULL,
    telefono character varying(128) NOT NULL,
    nombre character varying(128) NOT NULL,
    lista_rapida_id integer
);


ALTER TABLE public.ominicontacto_app_contactolistarapida OWNER TO omnileads;

--
-- TOC entry 337 (class 1259 OID 18040)
-- Name: ominicontacto_app_contactolistarapida_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_contactolistarapida_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_contactolistarapida_id_seq OWNER TO omnileads;

--
-- TOC entry 4943 (class 0 OID 0)
-- Dependencies: 337
-- Name: ominicontacto_app_contactolistarapida_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_contactolistarapida_id_seq OWNED BY public.ominicontacto_app_contactolistarapida.id;


--
-- TOC entry 236 (class 1259 OID 16644)
-- Name: ominicontacto_app_fieldformulario; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_fieldformulario (
    id integer NOT NULL,
    nombre_campo character varying(64) NOT NULL,
    orden integer NOT NULL,
    tipo integer NOT NULL,
    values_select text,
    is_required boolean NOT NULL,
    formulario_id integer NOT NULL,
    CONSTRAINT ominicontacto_app_fieldformulario_orden_check CHECK ((orden >= 0)),
    CONSTRAINT ominicontacto_app_fieldformulario_tipo_check CHECK ((tipo >= 0))
);


ALTER TABLE public.ominicontacto_app_fieldformulario OWNER TO omnileads;

--
-- TOC entry 235 (class 1259 OID 16642)
-- Name: ominicontacto_app_fieldformulario_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_fieldformulario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_fieldformulario_id_seq OWNER TO omnileads;

--
-- TOC entry 4945 (class 0 OID 0)
-- Dependencies: 235
-- Name: ominicontacto_app_fieldformulario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_fieldformulario_id_seq OWNED BY public.ominicontacto_app_fieldformulario.id;


--
-- TOC entry 238 (class 1259 OID 16657)
-- Name: ominicontacto_app_formulario; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_formulario (
    id integer NOT NULL,
    nombre character varying(64) NOT NULL,
    descripcion text NOT NULL,
    oculto boolean NOT NULL
);


ALTER TABLE public.ominicontacto_app_formulario OWNER TO omnileads;

--
-- TOC entry 237 (class 1259 OID 16655)
-- Name: ominicontacto_app_formulario_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_formulario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_formulario_id_seq OWNER TO omnileads;

--
-- TOC entry 4947 (class 0 OID 0)
-- Dependencies: 237
-- Name: ominicontacto_app_formulario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_formulario_id_seq OWNED BY public.ominicontacto_app_formulario.id;


--
-- TOC entry 240 (class 1259 OID 16680)
-- Name: ominicontacto_app_grabacion_marca; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_grabacion_marca (
    id integer NOT NULL,
    callid character varying(45) NOT NULL,
    descripcion text NOT NULL
);


ALTER TABLE public.ominicontacto_app_grabacion_marca OWNER TO omnileads;

--
-- TOC entry 239 (class 1259 OID 16678)
-- Name: ominicontacto_app_grabacion_marca_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_grabacion_marca_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_grabacion_marca_id_seq OWNER TO omnileads;

--
-- TOC entry 4949 (class 0 OID 0)
-- Dependencies: 239
-- Name: ominicontacto_app_grabacion_marca_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_grabacion_marca_id_seq OWNED BY public.ominicontacto_app_grabacion_marca.id;


--
-- TOC entry 242 (class 1259 OID 16691)
-- Name: ominicontacto_app_grupo; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_grupo (
    id integer NOT NULL,
    nombre character varying(20) NOT NULL,
    auto_attend_inbound boolean NOT NULL,
    auto_attend_dialer boolean NOT NULL,
    auto_unpause integer NOT NULL,
    obligar_calificacion boolean NOT NULL,
    call_off_camp boolean NOT NULL,
    acceso_grabaciones_agente boolean NOT NULL,
    acceso_dashboard_agente boolean NOT NULL,
    on_hold boolean NOT NULL,
    cantidad_agendas_personales integer,
    limitar_agendas_personales boolean NOT NULL,
    limitar_agendas_personales_en_dias boolean NOT NULL,
    tiempo_maximo_para_agendar integer,
    obligar_despausa boolean NOT NULL,
    show_console_timers boolean NOT NULL,
    acceso_agendas_agente boolean NOT NULL,
    acceso_calificaciones_agente boolean NOT NULL,
    acceso_campanas_preview_agente boolean NOT NULL,
    acceso_contactos_agente boolean NOT NULL,
    conjunto_de_pausa_id integer,
    CONSTRAINT ominicontacto_app_grupo_auto_unpause_check CHECK ((auto_unpause >= 0)),
    CONSTRAINT ominicontacto_app_grupo_cantidad_agendas_personales_check CHECK ((cantidad_agendas_personales >= 0)),
    CONSTRAINT ominicontacto_app_grupo_tiempo_maximo_para_agendar_check CHECK ((tiempo_maximo_para_agendar >= 0))
);


ALTER TABLE public.ominicontacto_app_grupo OWNER TO omnileads;

--
-- TOC entry 241 (class 1259 OID 16689)
-- Name: ominicontacto_app_grupo_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_grupo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_grupo_id_seq OWNER TO omnileads;

--
-- TOC entry 4951 (class 0 OID 0)
-- Dependencies: 241
-- Name: ominicontacto_app_grupo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_grupo_id_seq OWNED BY public.ominicontacto_app_grupo.id;


--
-- TOC entry 244 (class 1259 OID 16700)
-- Name: ominicontacto_app_historicalcalificacioncliente; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_historicalcalificacioncliente (
    id integer NOT NULL,
    fecha timestamp with time zone NOT NULL,
    observaciones text,
    agendado boolean NOT NULL,
    es_calificacion_manual boolean NOT NULL,
    history_id integer NOT NULL,
    history_date timestamp with time zone NOT NULL,
    history_change_reason character varying(100),
    history_type character varying(1) NOT NULL,
    agente_id integer,
    contacto_id integer,
    history_user_id integer,
    opcion_calificacion_id integer,
    callid character varying(32),
    created timestamp with time zone NOT NULL,
    modified timestamp with time zone NOT NULL,
    tipo_agenda integer,
    CONSTRAINT ominicontacto_app_historicalcalificacionclien_tipo_agenda_check CHECK ((tipo_agenda >= 0))
);


ALTER TABLE public.ominicontacto_app_historicalcalificacioncliente OWNER TO omnileads;

--
-- TOC entry 243 (class 1259 OID 16698)
-- Name: ominicontacto_app_historicalcalificacioncliente_history_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_historicalcalificacioncliente_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_historicalcalificacioncliente_history_id_seq OWNER TO omnileads;

--
-- TOC entry 4953 (class 0 OID 0)
-- Dependencies: 243
-- Name: ominicontacto_app_historicalcalificacioncliente_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_historicalcalificacioncliente_history_id_seq OWNED BY public.ominicontacto_app_historicalcalificacioncliente.history_id;


--
-- TOC entry 334 (class 1259 OID 18009)
-- Name: ominicontacto_app_historicalrespuestaformulariogestion; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_historicalrespuestaformulariogestion (
    id integer NOT NULL,
    metadata text NOT NULL,
    fecha timestamp with time zone NOT NULL,
    history_id integer NOT NULL,
    history_date timestamp with time zone NOT NULL,
    history_change_reason character varying(100),
    history_type character varying(1) NOT NULL,
    calificacion_id integer,
    history_user_id integer
);


ALTER TABLE public.ominicontacto_app_historicalrespuestaformulariogestion OWNER TO omnileads;

--
-- TOC entry 333 (class 1259 OID 18007)
-- Name: ominicontacto_app_historicalrespuestaformulariog_history_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_historicalrespuestaformulariog_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_historicalrespuestaformulariog_history_id_seq OWNER TO omnileads;

--
-- TOC entry 4955 (class 0 OID 0)
-- Dependencies: 333
-- Name: ominicontacto_app_historicalrespuestaformulariog_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_historicalrespuestaformulariog_history_id_seq OWNED BY public.ominicontacto_app_historicalrespuestaformulariogestion.history_id;


--
-- TOC entry 336 (class 1259 OID 18028)
-- Name: ominicontacto_app_listasrapidas; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_listasrapidas (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL,
    fecha_alta timestamp with time zone NOT NULL,
    archivo_importacion character varying(256) NOT NULL,
    nombre_archivo_importacion character varying(256) NOT NULL,
    cantidad_contactos integer NOT NULL,
    metadata text,
    CONSTRAINT ominicontacto_app_listasrapidas_cantidad_contactos_check CHECK ((cantidad_contactos >= 0))
);


ALTER TABLE public.ominicontacto_app_listasrapidas OWNER TO omnileads;

--
-- TOC entry 335 (class 1259 OID 18026)
-- Name: ominicontacto_app_listasrapidas_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_listasrapidas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_listasrapidas_id_seq OWNER TO omnileads;

--
-- TOC entry 4957 (class 0 OID 0)
-- Dependencies: 335
-- Name: ominicontacto_app_listasrapidas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_listasrapidas_id_seq OWNED BY public.ominicontacto_app_listasrapidas.id;


--
-- TOC entry 246 (class 1259 OID 16711)
-- Name: ominicontacto_app_mensajechat; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_mensajechat (
    id integer NOT NULL,
    mensaje text NOT NULL,
    fecha_hora timestamp with time zone NOT NULL,
    chat_id integer NOT NULL,
    sender_id integer NOT NULL,
    to_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_mensajechat OWNER TO omnileads;

--
-- TOC entry 245 (class 1259 OID 16709)
-- Name: ominicontacto_app_mensajechat_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_mensajechat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_mensajechat_id_seq OWNER TO omnileads;

--
-- TOC entry 4959 (class 0 OID 0)
-- Dependencies: 245
-- Name: ominicontacto_app_mensajechat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_mensajechat_id_seq OWNED BY public.ominicontacto_app_mensajechat.id;


--
-- TOC entry 248 (class 1259 OID 16744)
-- Name: ominicontacto_app_respuestaformulariogestion; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_respuestaformulariogestion (
    id integer NOT NULL,
    metadata text NOT NULL,
    fecha timestamp with time zone NOT NULL,
    calificacion_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_respuestaformulariogestion OWNER TO omnileads;

--
-- TOC entry 247 (class 1259 OID 16742)
-- Name: ominicontacto_app_metadatacliente_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_metadatacliente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_metadatacliente_id_seq OWNER TO omnileads;

--
-- TOC entry 4961 (class 0 OID 0)
-- Dependencies: 247
-- Name: ominicontacto_app_metadatacliente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_metadatacliente_id_seq OWNED BY public.ominicontacto_app_respuestaformulariogestion.id;


--
-- TOC entry 250 (class 1259 OID 16763)
-- Name: ominicontacto_app_nombrecalificacion; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_nombrecalificacion (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL
);


ALTER TABLE public.ominicontacto_app_nombrecalificacion OWNER TO omnileads;

--
-- TOC entry 249 (class 1259 OID 16761)
-- Name: ominicontacto_app_nombrecalificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_nombrecalificacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_nombrecalificacion_id_seq OWNER TO omnileads;

--
-- TOC entry 4963 (class 0 OID 0)
-- Dependencies: 249
-- Name: ominicontacto_app_nombrecalificacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_nombrecalificacion_id_seq OWNED BY public.ominicontacto_app_nombrecalificacion.id;


--
-- TOC entry 252 (class 1259 OID 16771)
-- Name: ominicontacto_app_opcioncalificacion; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_opcioncalificacion (
    id integer NOT NULL,
    tipo integer NOT NULL,
    nombre character varying(50) NOT NULL,
    campana_id integer NOT NULL,
    formulario_id integer,
    oculta boolean NOT NULL,
    positiva boolean NOT NULL,
    interaccion_crm boolean NOT NULL
);


ALTER TABLE public.ominicontacto_app_opcioncalificacion OWNER TO omnileads;

--
-- TOC entry 251 (class 1259 OID 16769)
-- Name: ominicontacto_app_opcioncalificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_opcioncalificacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_opcioncalificacion_id_seq OWNER TO omnileads;

--
-- TOC entry 4965 (class 0 OID 0)
-- Dependencies: 251
-- Name: ominicontacto_app_opcioncalificacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_opcioncalificacion_id_seq OWNED BY public.ominicontacto_app_opcioncalificacion.id;


--
-- TOC entry 294 (class 1259 OID 17488)
-- Name: ominicontacto_app_parametroscrm; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_parametroscrm (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL,
    valor character varying(256) NOT NULL,
    tipo integer NOT NULL,
    campana_id integer NOT NULL,
    CONSTRAINT ominicontacto_app_parametroscrm_tipo_check CHECK ((tipo >= 0))
);


ALTER TABLE public.ominicontacto_app_parametroscrm OWNER TO omnileads;

--
-- TOC entry 293 (class 1259 OID 17486)
-- Name: ominicontacto_app_parametroscrm_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_parametroscrm_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_parametroscrm_id_seq OWNER TO omnileads;

--
-- TOC entry 4967 (class 0 OID 0)
-- Dependencies: 293
-- Name: ominicontacto_app_parametroscrm_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_parametroscrm_id_seq OWNED BY public.ominicontacto_app_parametroscrm.id;


--
-- TOC entry 254 (class 1259 OID 16787)
-- Name: ominicontacto_app_pausa; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_pausa (
    id integer NOT NULL,
    nombre character varying(20) NOT NULL,
    tipo character varying(1) NOT NULL,
    eliminada boolean NOT NULL
);


ALTER TABLE public.ominicontacto_app_pausa OWNER TO omnileads;

--
-- TOC entry 253 (class 1259 OID 16785)
-- Name: ominicontacto_app_pausa_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_pausa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_pausa_id_seq OWNER TO omnileads;

--
-- TOC entry 4969 (class 0 OID 0)
-- Dependencies: 253
-- Name: ominicontacto_app_pausa_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_pausa_id_seq OWNED BY public.ominicontacto_app_pausa.id;


--
-- TOC entry 330 (class 1259 OID 17970)
-- Name: ominicontacto_app_reglaincidenciaporcalificacion; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_reglaincidenciaporcalificacion (
    id integer NOT NULL,
    intento_max integer NOT NULL,
    reintentar_tarde integer NOT NULL,
    en_modo integer NOT NULL,
    opcion_calificacion_id integer NOT NULL,
    CONSTRAINT ominicontacto_app_reglaincidenciaporcalificacion_en_modo_check CHECK ((en_modo >= 0))
);


ALTER TABLE public.ominicontacto_app_reglaincidenciaporcalificacion OWNER TO omnileads;

--
-- TOC entry 329 (class 1259 OID 17968)
-- Name: ominicontacto_app_reglaincidenciaporcalificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_reglaincidenciaporcalificacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_reglaincidenciaporcalificacion_id_seq OWNER TO omnileads;

--
-- TOC entry 4971 (class 0 OID 0)
-- Dependencies: 329
-- Name: ominicontacto_app_reglaincidenciaporcalificacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_reglaincidenciaporcalificacion_id_seq OWNED BY public.ominicontacto_app_reglaincidenciaporcalificacion.id;


--
-- TOC entry 259 (class 1259 OID 16819)
-- Name: ominicontacto_app_reglasincidencia; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_reglasincidencia (
    id integer NOT NULL,
    estado integer NOT NULL,
    estado_personalizado character varying(128),
    intento_max integer NOT NULL,
    reintentar_tarde integer NOT NULL,
    en_modo integer NOT NULL,
    campana_id integer NOT NULL,
    CONSTRAINT ominicontacto_app_reglasincidencia_en_modo_check CHECK ((en_modo >= 0)),
    CONSTRAINT ominicontacto_app_reglasincidencia_estado_check CHECK ((estado >= 0))
);


ALTER TABLE public.ominicontacto_app_reglasincidencia OWNER TO omnileads;

--
-- TOC entry 258 (class 1259 OID 16817)
-- Name: ominicontacto_app_reglasincidencia_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_reglasincidencia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_reglasincidencia_id_seq OWNER TO omnileads;

--
-- TOC entry 4973 (class 0 OID 0)
-- Dependencies: 258
-- Name: ominicontacto_app_reglasincidencia_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_reglasincidencia_id_seq OWNED BY public.ominicontacto_app_reglasincidencia.id;


--
-- TOC entry 320 (class 1259 OID 17780)
-- Name: ominicontacto_app_sistemaexterno; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_sistemaexterno (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL
);


ALTER TABLE public.ominicontacto_app_sistemaexterno OWNER TO omnileads;

--
-- TOC entry 319 (class 1259 OID 17778)
-- Name: ominicontacto_app_sistemaexterno_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_sistemaexterno_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_sistemaexterno_id_seq OWNER TO omnileads;

--
-- TOC entry 4975 (class 0 OID 0)
-- Dependencies: 319
-- Name: ominicontacto_app_sistemaexterno_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_sistemaexterno_id_seq OWNED BY public.ominicontacto_app_sistemaexterno.id;


--
-- TOC entry 261 (class 1259 OID 16829)
-- Name: ominicontacto_app_sitioexterno; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_sitioexterno (
    id integer NOT NULL,
    nombre character varying(128) NOT NULL,
    url character varying(250) NOT NULL,
    oculto boolean NOT NULL,
    metodo integer NOT NULL,
    disparador integer NOT NULL,
    formato integer,
    objetivo integer,
    autenticacion_id integer,
    CONSTRAINT ominicontacto_app_sitioexterno_disparador_check CHECK ((disparador >= 0)),
    CONSTRAINT ominicontacto_app_sitioexterno_formato_check CHECK ((formato >= 0)),
    CONSTRAINT ominicontacto_app_sitioexterno_metodo_check CHECK ((metodo >= 0)),
    CONSTRAINT ominicontacto_app_sitioexterno_objetivo_check CHECK ((objetivo >= 0))
);


ALTER TABLE public.ominicontacto_app_sitioexterno OWNER TO omnileads;

--
-- TOC entry 260 (class 1259 OID 16827)
-- Name: ominicontacto_app_sitioexterno_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_sitioexterno_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_sitioexterno_id_seq OWNER TO omnileads;

--
-- TOC entry 4977 (class 0 OID 0)
-- Dependencies: 260
-- Name: ominicontacto_app_sitioexterno_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_sitioexterno_id_seq OWNED BY public.ominicontacto_app_sitioexterno.id;


--
-- TOC entry 263 (class 1259 OID 16837)
-- Name: ominicontacto_app_supervisorprofile; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_supervisorprofile (
    id integer NOT NULL,
    sip_extension integer NOT NULL,
    sip_password character varying(128),
    is_administrador boolean NOT NULL,
    is_customer boolean NOT NULL,
    borrado boolean NOT NULL,
    "timestamp" character varying(64),
    user_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_supervisorprofile OWNER TO omnileads;

--
-- TOC entry 262 (class 1259 OID 16835)
-- Name: ominicontacto_app_supervisorprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_supervisorprofile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_supervisorprofile_id_seq OWNER TO omnileads;

--
-- TOC entry 4979 (class 0 OID 0)
-- Dependencies: 262
-- Name: ominicontacto_app_supervisorprofile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_supervisorprofile_id_seq OWNED BY public.ominicontacto_app_supervisorprofile.id;


--
-- TOC entry 208 (class 1259 OID 16463)
-- Name: ominicontacto_app_user; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(30) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    is_agente boolean NOT NULL,
    is_supervisor boolean NOT NULL,
    last_session_key character varying(40),
    borrado boolean NOT NULL,
    is_cliente_webphone boolean NOT NULL
);


ALTER TABLE public.ominicontacto_app_user OWNER TO omnileads;

--
-- TOC entry 210 (class 1259 OID 16476)
-- Name: ominicontacto_app_user_groups; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_user_groups OWNER TO omnileads;

--
-- TOC entry 209 (class 1259 OID 16474)
-- Name: ominicontacto_app_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_user_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_user_groups_id_seq OWNER TO omnileads;

--
-- TOC entry 4982 (class 0 OID 0)
-- Dependencies: 209
-- Name: ominicontacto_app_user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_user_groups_id_seq OWNED BY public.ominicontacto_app_user_groups.id;


--
-- TOC entry 207 (class 1259 OID 16461)
-- Name: ominicontacto_app_user_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_user_id_seq OWNER TO omnileads;

--
-- TOC entry 4983 (class 0 OID 0)
-- Dependencies: 207
-- Name: ominicontacto_app_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_user_id_seq OWNED BY public.ominicontacto_app_user.id;


--
-- TOC entry 212 (class 1259 OID 16484)
-- Name: ominicontacto_app_user_user_permissions; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.ominicontacto_app_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.ominicontacto_app_user_user_permissions OWNER TO omnileads;

--
-- TOC entry 211 (class 1259 OID 16482)
-- Name: ominicontacto_app_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.ominicontacto_app_user_user_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ominicontacto_app_user_user_permissions_id_seq OWNER TO omnileads;

--
-- TOC entry 4985 (class 0 OID 0)
-- Dependencies: 211
-- Name: ominicontacto_app_user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.ominicontacto_app_user_user_permissions_id_seq OWNED BY public.ominicontacto_app_user_user_permissions.id;


--
-- TOC entry 350 (class 1259 OID 18189)
-- Name: queue_log; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.queue_log (
    id integer NOT NULL,
    "time" character varying(100) DEFAULT NULL::character varying,
    callid character varying(100) DEFAULT ''::character varying NOT NULL,
    queuename character varying(100) DEFAULT ''::character varying NOT NULL,
    agent character varying(100) DEFAULT ''::character varying NOT NULL,
    event character varying(100) DEFAULT ''::character varying NOT NULL,
    data1 character varying(100) DEFAULT ''::character varying NOT NULL,
    data2 character varying(100) DEFAULT ''::character varying NOT NULL,
    data3 character varying(100) DEFAULT ''::character varying NOT NULL,
    data4 character varying(100) DEFAULT ''::character varying NOT NULL,
    data5 character varying(100) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE public.queue_log OWNER TO omnileads;

--
-- TOC entry 349 (class 1259 OID 18187)
-- Name: queue_log_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.queue_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.queue_log_id_seq OWNER TO omnileads;

--
-- TOC entry 4987 (class 0 OID 0)
-- Dependencies: 349
-- Name: queue_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.queue_log_id_seq OWNED BY public.queue_log.id;


--
-- TOC entry 257 (class 1259 OID 16808)
-- Name: queue_member_table; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.queue_member_table (
    id integer NOT NULL,
    membername character varying(128) NOT NULL,
    interface character varying(128) NOT NULL,
    penalty integer NOT NULL,
    paused integer NOT NULL,
    id_campana character varying(128) NOT NULL,
    member_id integer NOT NULL,
    queue_name character varying(128) NOT NULL
);


ALTER TABLE public.queue_member_table OWNER TO omnileads;

--
-- TOC entry 256 (class 1259 OID 16806)
-- Name: queue_member_table_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.queue_member_table_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.queue_member_table_id_seq OWNER TO omnileads;

--
-- TOC entry 4989 (class 0 OID 0)
-- Dependencies: 256
-- Name: queue_member_table_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.queue_member_table_id_seq OWNED BY public.queue_member_table.id;


--
-- TOC entry 255 (class 1259 OID 16795)
-- Name: queue_table; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.queue_table (
    name character varying(128) NOT NULL,
    timeout bigint,
    retry bigint,
    maxlen bigint NOT NULL,
    wrapuptime bigint NOT NULL,
    servicelevel bigint NOT NULL,
    strategy character varying(128) NOT NULL,
    eventmemberstatus boolean NOT NULL,
    eventwhencalled boolean NOT NULL,
    weight bigint NOT NULL,
    ringinuse boolean NOT NULL,
    setinterfacevar boolean NOT NULL,
    wait integer NOT NULL,
    auto_grabacion boolean NOT NULL,
    detectar_contestadores boolean NOT NULL,
    ep_id_wombat integer,
    announce character varying(128),
    announce_frequency bigint,
    initial_predictive_model boolean NOT NULL,
    initial_boost_factor numeric(3,1),
    musiconhold_id integer,
    context character varying(128),
    monitor_join boolean,
    monitor_format character varying(128),
    queue_youarenext character varying(128),
    queue_thereare character varying(128),
    queue_callswaiting character varying(128),
    queue_holdtime character varying(128),
    queue_minutes character varying(128),
    queue_seconds character varying(128),
    queue_lessthan character varying(128),
    queue_thankyou character varying(128),
    queue_reporthold character varying(128),
    announce_round_seconds bigint,
    announce_holdtime character varying(128) NOT NULL,
    joinempty character varying(128),
    leavewhenempty character varying(128),
    reportholdtime boolean,
    memberdelay bigint,
    timeoutrestart boolean,
    audio_de_ingreso_id integer,
    audio_para_contestadores_id integer,
    audios_id integer,
    campana_id integer,
    dial_timeout integer,
    destino_id integer,
    ivr_breakdown_id integer,
    announce_position boolean NOT NULL,
    wait_announce_frequency bigint,
    audio_previo_conexion_llamada_id integer,
    CONSTRAINT queue_table_dial_timeout_check CHECK ((dial_timeout >= 0)),
    CONSTRAINT queue_table_wait_check CHECK ((wait >= 0))
);


ALTER TABLE public.queue_table OWNER TO omnileads;

--
-- TOC entry 346 (class 1259 OID 18166)
-- Name: reportes_app_actividadagentelog; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.reportes_app_actividadagentelog (
    id integer NOT NULL,
    "time" timestamp with time zone NOT NULL,
    agente_id integer,
    event character varying(32),
    pausa_id character varying(128)
);


ALTER TABLE public.reportes_app_actividadagentelog OWNER TO omnileads;

--
-- TOC entry 345 (class 1259 OID 18164)
-- Name: reportes_app_actividadagentelog_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.reportes_app_actividadagentelog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reportes_app_actividadagentelog_id_seq OWNER TO omnileads;

--
-- TOC entry 4992 (class 0 OID 0)
-- Dependencies: 345
-- Name: reportes_app_actividadagentelog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.reportes_app_actividadagentelog_id_seq OWNED BY public.reportes_app_actividadagentelog.id;


--
-- TOC entry 348 (class 1259 OID 18174)
-- Name: reportes_app_llamadalog; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.reportes_app_llamadalog (
    id integer NOT NULL,
    "time" timestamp with time zone NOT NULL,
    callid character varying(32),
    campana_id integer,
    tipo_campana integer,
    tipo_llamada integer,
    agente_id integer,
    event character varying(32),
    numero_marcado character varying(128),
    contacto_id integer,
    bridge_wait_time integer,
    duracion_llamada integer,
    archivo_grabacion character varying(100),
    agente_extra_id integer,
    campana_extra_id integer,
    numero_extra character varying(128)
);


ALTER TABLE public.reportes_app_llamadalog OWNER TO omnileads;

--
-- TOC entry 347 (class 1259 OID 18172)
-- Name: reportes_app_llamadalog_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.reportes_app_llamadalog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reportes_app_llamadalog_id_seq OWNER TO omnileads;

--
-- TOC entry 4994 (class 0 OID 0)
-- Dependencies: 347
-- Name: reportes_app_llamadalog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.reportes_app_llamadalog_id_seq OWNED BY public.reportes_app_llamadalog.id;


--
-- TOC entry 352 (class 1259 OID 18218)
-- Name: reportes_app_transferenciaaencuestalog; Type: TABLE; Schema: public; Owner: omnileads
--

CREATE TABLE public.reportes_app_transferenciaaencuestalog (
    id integer NOT NULL,
    "time" timestamp with time zone NOT NULL,
    agente_id integer,
    campana_id integer,
    encuesta_id integer,
    callid character varying(32)
);


ALTER TABLE public.reportes_app_transferenciaaencuestalog OWNER TO omnileads;

--
-- TOC entry 351 (class 1259 OID 18216)
-- Name: reportes_app_transferenciaaencuestalog_id_seq; Type: SEQUENCE; Schema: public; Owner: omnileads
--

CREATE SEQUENCE public.reportes_app_transferenciaaencuestalog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reportes_app_transferenciaaencuestalog_id_seq OWNER TO omnileads;

--
-- TOC entry 4996 (class 0 OID 0)
-- Dependencies: 351
-- Name: reportes_app_transferenciaaencuestalog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnileads
--

ALTER SEQUENCE public.reportes_app_transferenciaaencuestalog_id_seq OWNED BY public.reportes_app_transferenciaaencuestalog.id;


--
-- TOC entry 4071 (class 2604 OID 16425)
-- Name: auth_group id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_group ALTER COLUMN id SET DEFAULT nextval('public.auth_group_id_seq'::regclass);


--
-- TOC entry 4072 (class 2604 OID 16435)
-- Name: auth_group_permissions id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_group_permissions_id_seq'::regclass);


--
-- TOC entry 4070 (class 2604 OID 16417)
-- Name: auth_permission id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_permission ALTER COLUMN id SET DEFAULT nextval('public.auth_permission_id_seq'::regclass);


--
-- TOC entry 4120 (class 2604 OID 17615)
-- Name: configuracion_telefonia_app_amdconf id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_amdconf ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_amdconf_id_seq'::regclass);


--
-- TOC entry 4122 (class 2604 OID 17640)
-- Name: configuracion_telefonia_app_audiosasteriskconf id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_audiosasteriskconf ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_audiosasteriskconf_id_seq'::regclass);


--
-- TOC entry 4103 (class 2604 OID 17244)
-- Name: configuracion_telefonia_app_destinoentrante id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_destinoentrante ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_destinoentrante_id_seq'::regclass);


--
-- TOC entry 4117 (class 2604 OID 17571)
-- Name: configuracion_telefonia_app_destinopersonalizado id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_destinopersonalizado ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_destinopersonalizado_id_seq'::regclass);


--
-- TOC entry 4121 (class 2604 OID 17632)
-- Name: configuracion_telefonia_app_esquemagrabaciones id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_esquemagrabaciones ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_esquemagrabaciones_id_seq'::regclass);


--
-- TOC entry 4104 (class 2604 OID 17256)
-- Name: configuracion_telefonia_app_grupohorario id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_grupohorario ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_grupohorario_id_seq'::regclass);


--
-- TOC entry 4114 (class 2604 OID 17456)
-- Name: configuracion_telefonia_app_hangup id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_hangup ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_hangup_id_seq'::regclass);


--
-- TOC entry 4116 (class 2604 OID 17548)
-- Name: configuracion_telefonia_app_identificadorcliente id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_identificadorcliente ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_identificadorcliente_id_seq'::regclass);


--
-- TOC entry 4105 (class 2604 OID 17266)
-- Name: configuracion_telefonia_app_ivr id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ivr ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_ivr_id_seq'::regclass);


--
-- TOC entry 4118 (class 2604 OID 17587)
-- Name: configuracion_telefonia_app_musicadeespera id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_musicadeespera ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_musicadeespera_id_seq'::regclass);


--
-- TOC entry 4106 (class 2604 OID 17279)
-- Name: configuracion_telefonia_app_opciondestino id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_opciondestino ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_opciondestino_id_seq'::regclass);


--
-- TOC entry 4107 (class 2604 OID 17287)
-- Name: configuracion_telefonia_app_ordentroncal id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ordentroncal ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_ordentroncal_id_seq'::regclass);


--
-- TOC entry 4108 (class 2604 OID 17296)
-- Name: configuracion_telefonia_app_patrondediscado id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_patrondediscado ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_patrondediscado_id_seq'::regclass);


--
-- TOC entry 4119 (class 2604 OID 17597)
-- Name: configuracion_telefonia_app_playlist id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_playlist ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_playlist_id_seq'::regclass);


--
-- TOC entry 4109 (class 2604 OID 17305)
-- Name: configuracion_telefonia_app_rutaentrante id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_rutaentrante ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_rutaentrante_id_seq'::regclass);


--
-- TOC entry 4110 (class 2604 OID 17318)
-- Name: configuracion_telefonia_app_rutasaliente id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_rutasaliente ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_rutasaliente_id_seq'::regclass);


--
-- TOC entry 4111 (class 2604 OID 17332)
-- Name: configuracion_telefonia_app_troncalsip id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_troncalsip ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_troncalsip_id_seq'::regclass);


--
-- TOC entry 4112 (class 2604 OID 17346)
-- Name: configuracion_telefonia_app_validacionfechahora id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_validacionfechahora ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_validacionfechahora_id_seq'::regclass);


--
-- TOC entry 4113 (class 2604 OID 17356)
-- Name: configuracion_telefonia_app_validaciontiempo id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_validaciontiempo ALTER COLUMN id SET DEFAULT nextval('public.configuracion_telefonia_app_validaciontiempo_id_seq'::regclass);


--
-- TOC entry 4123 (class 2604 OID 17648)
-- Name: constance_config id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.constance_config ALTER COLUMN id SET DEFAULT nextval('public.constance_config_id_seq'::regclass);


--
-- TOC entry 4124 (class 2604 OID 17662)
-- Name: defender_accessattempt id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.defender_accessattempt ALTER COLUMN id SET DEFAULT nextval('public.defender_accessattempt_id_seq'::regclass);


--
-- TOC entry 4102 (class 2604 OID 17195)
-- Name: django_admin_log id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_admin_log ALTER COLUMN id SET DEFAULT nextval('public.django_admin_log_id_seq'::regclass);


--
-- TOC entry 4069 (class 2604 OID 16407)
-- Name: django_content_type id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_content_type ALTER COLUMN id SET DEFAULT nextval('public.django_content_type_id_seq'::regclass);


--
-- TOC entry 4068 (class 2604 OID 16396)
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_migrations ALTER COLUMN id SET DEFAULT nextval('public.django_migrations_id_seq'::regclass);


--
-- TOC entry 4125 (class 2604 OID 17673)
-- Name: easyaudit_crudevent id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.easyaudit_crudevent ALTER COLUMN id SET DEFAULT nextval('public.easyaudit_crudevent_id_seq'::regclass);


--
-- TOC entry 4126 (class 2604 OID 17684)
-- Name: easyaudit_loginevent id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.easyaudit_loginevent ALTER COLUMN id SET DEFAULT nextval('public.easyaudit_loginevent_id_seq'::regclass);


--
-- TOC entry 4127 (class 2604 OID 17721)
-- Name: easyaudit_requestevent id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.easyaudit_requestevent ALTER COLUMN id SET DEFAULT nextval('public.easyaudit_requestevent_id_seq'::regclass);


--
-- TOC entry 4155 (class 2604 OID 18338)
-- Name: form_app_encuesta id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.form_app_encuesta ALTER COLUMN id SET DEFAULT nextval('public.form_app_encuesta_id_seq'::regclass);


--
-- TOC entry 4156 (class 2604 OID 18346)
-- Name: form_app_formulario id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.form_app_formulario ALTER COLUMN id SET DEFAULT nextval('public.form_app_formulario_id_seq'::regclass);


--
-- TOC entry 4076 (class 2604 OID 16495)
-- Name: ominicontacto_app_actuacionvigente id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_actuacionvigente ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_actuacionvigente_id_seq'::regclass);


--
-- TOC entry 4077 (class 2604 OID 16515)
-- Name: ominicontacto_app_agendacontacto id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agendacontacto ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_agendacontacto_id_seq'::regclass);


--
-- TOC entry 4078 (class 2604 OID 16527)
-- Name: ominicontacto_app_agenteencontacto id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteencontacto ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_agenteencontacto_id_seq'::regclass);


--
-- TOC entry 4129 (class 2604 OID 17794)
-- Name: ominicontacto_app_agenteensistemaexterno id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteensistemaexterno ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_agenteensistemaexterno_id_seq'::regclass);


--
-- TOC entry 4079 (class 2604 OID 16539)
-- Name: ominicontacto_app_agenteprofile id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteprofile ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_agenteprofile_id_seq'::regclass);


--
-- TOC entry 4080 (class 2604 OID 16550)
-- Name: ominicontacto_app_archivodeaudio id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_archivodeaudio ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_archivodeaudio_id_seq'::regclass);


--
-- TOC entry 4131 (class 2604 OID 17923)
-- Name: ominicontacto_app_auditoriacalificacion id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_auditoriacalificacion ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_auditoriacalificacion_id_seq'::regclass);


--
-- TOC entry 4140 (class 2604 OID 18141)
-- Name: ominicontacto_app_autenticacionsitioexterno id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_autenticacionsitioexterno ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_autenticacionsitioexterno_id_seq'::regclass);


--
-- TOC entry 4082 (class 2604 OID 16572)
-- Name: ominicontacto_app_basedatoscontacto id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_basedatoscontacto ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_basedatoscontacto_id_seq'::regclass);


--
-- TOC entry 4081 (class 2604 OID 16560)
-- Name: ominicontacto_app_blacklist id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_blacklist ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_backlist_id_seq'::regclass);


--
-- TOC entry 4083 (class 2604 OID 16585)
-- Name: ominicontacto_app_calificacioncliente id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_calificacioncliente ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_calificacioncliente_id_seq'::regclass);


--
-- TOC entry 4084 (class 2604 OID 16596)
-- Name: ominicontacto_app_campana id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_campana_id_seq'::regclass);


--
-- TOC entry 4101 (class 2604 OID 16862)
-- Name: ominicontacto_app_campana_supervisors id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana_supervisors ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_campana_supervisors_id_seq'::regclass);


--
-- TOC entry 4085 (class 2604 OID 16611)
-- Name: ominicontacto_app_chat id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_chat ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_chat_id_seq'::regclass);


--
-- TOC entry 4130 (class 2604 OID 17839)
-- Name: ominicontacto_app_clientewebphoneprofile id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_clientewebphoneprofile ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_clientewebphoneprofile_id_seq'::regclass);


--
-- TOC entry 4134 (class 2604 OID 17995)
-- Name: ominicontacto_app_configuraciondeagentesdecampana id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_configuraciondeagentesdecampana ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_configuraciondeagentesdecampana_id_seq'::regclass);


--
-- TOC entry 4139 (class 2604 OID 18091)
-- Name: ominicontacto_app_configuraciondepausa id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_configuraciondepausa ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_configuraciondepausa_id_seq'::regclass);


--
-- TOC entry 4138 (class 2604 OID 18083)
-- Name: ominicontacto_app_conjuntodepausa id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_conjuntodepausa ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_conjuntodepausa_id_seq'::regclass);


--
-- TOC entry 4086 (class 2604 OID 16619)
-- Name: ominicontacto_app_contacto id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contacto ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_contacto_id_seq'::regclass);


--
-- TOC entry 4132 (class 2604 OID 17947)
-- Name: ominicontacto_app_contactoblacklist id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contactoblacklist ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_contactoblacklist_id_seq'::regclass);


--
-- TOC entry 4137 (class 2604 OID 18045)
-- Name: ominicontacto_app_contactolistarapida id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contactolistarapida ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_contactolistarapida_id_seq'::regclass);


--
-- TOC entry 4087 (class 2604 OID 16647)
-- Name: ominicontacto_app_fieldformulario id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_fieldformulario ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_fieldformulario_id_seq'::regclass);


--
-- TOC entry 4088 (class 2604 OID 16660)
-- Name: ominicontacto_app_formulario id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_formulario ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_formulario_id_seq'::regclass);


--
-- TOC entry 4089 (class 2604 OID 16683)
-- Name: ominicontacto_app_grabacion_marca id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_grabacion_marca ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_grabacion_marca_id_seq'::regclass);


--
-- TOC entry 4090 (class 2604 OID 16694)
-- Name: ominicontacto_app_grupo id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_grupo ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_grupo_id_seq'::regclass);


--
-- TOC entry 4091 (class 2604 OID 16703)
-- Name: ominicontacto_app_historicalcalificacioncliente history_id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_historicalcalificacioncliente ALTER COLUMN history_id SET DEFAULT nextval('public.ominicontacto_app_historicalcalificacioncliente_history_id_seq'::regclass);


--
-- TOC entry 4135 (class 2604 OID 18012)
-- Name: ominicontacto_app_historicalrespuestaformulariogestion history_id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_historicalrespuestaformulariogestion ALTER COLUMN history_id SET DEFAULT nextval('public.ominicontacto_app_historicalrespuestaformulariog_history_id_seq'::regclass);


--
-- TOC entry 4136 (class 2604 OID 18031)
-- Name: ominicontacto_app_listasrapidas id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_listasrapidas ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_listasrapidas_id_seq'::regclass);


--
-- TOC entry 4092 (class 2604 OID 16714)
-- Name: ominicontacto_app_mensajechat id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_mensajechat ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_mensajechat_id_seq'::regclass);


--
-- TOC entry 4094 (class 2604 OID 16766)
-- Name: ominicontacto_app_nombrecalificacion id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_nombrecalificacion ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_nombrecalificacion_id_seq'::regclass);


--
-- TOC entry 4095 (class 2604 OID 16774)
-- Name: ominicontacto_app_opcioncalificacion id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_opcioncalificacion ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_opcioncalificacion_id_seq'::regclass);


--
-- TOC entry 4115 (class 2604 OID 17491)
-- Name: ominicontacto_app_parametroscrm id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_parametroscrm ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_parametroscrm_id_seq'::regclass);


--
-- TOC entry 4096 (class 2604 OID 16790)
-- Name: ominicontacto_app_pausa id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_pausa ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_pausa_id_seq'::regclass);


--
-- TOC entry 4133 (class 2604 OID 17973)
-- Name: ominicontacto_app_reglaincidenciaporcalificacion id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_reglaincidenciaporcalificacion ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_reglaincidenciaporcalificacion_id_seq'::regclass);


--
-- TOC entry 4098 (class 2604 OID 16822)
-- Name: ominicontacto_app_reglasincidencia id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_reglasincidencia ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_reglasincidencia_id_seq'::regclass);


--
-- TOC entry 4093 (class 2604 OID 16747)
-- Name: ominicontacto_app_respuestaformulariogestion id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_respuestaformulariogestion ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_metadatacliente_id_seq'::regclass);


--
-- TOC entry 4128 (class 2604 OID 17783)
-- Name: ominicontacto_app_sistemaexterno id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_sistemaexterno ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_sistemaexterno_id_seq'::regclass);


--
-- TOC entry 4099 (class 2604 OID 16832)
-- Name: ominicontacto_app_sitioexterno id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_sitioexterno ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_sitioexterno_id_seq'::regclass);


--
-- TOC entry 4100 (class 2604 OID 16840)
-- Name: ominicontacto_app_supervisorprofile id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_supervisorprofile ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_supervisorprofile_id_seq'::regclass);


--
-- TOC entry 4073 (class 2604 OID 16466)
-- Name: ominicontacto_app_user id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_user_id_seq'::regclass);


--
-- TOC entry 4074 (class 2604 OID 16479)
-- Name: ominicontacto_app_user_groups id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_groups ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_user_groups_id_seq'::regclass);


--
-- TOC entry 4075 (class 2604 OID 16487)
-- Name: ominicontacto_app_user_user_permissions id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('public.ominicontacto_app_user_user_permissions_id_seq'::regclass);


--
-- TOC entry 4143 (class 2604 OID 18192)
-- Name: queue_log id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_log ALTER COLUMN id SET DEFAULT nextval('public.queue_log_id_seq'::regclass);


--
-- TOC entry 4097 (class 2604 OID 16811)
-- Name: queue_member_table id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_member_table ALTER COLUMN id SET DEFAULT nextval('public.queue_member_table_id_seq'::regclass);


--
-- TOC entry 4141 (class 2604 OID 18169)
-- Name: reportes_app_actividadagentelog id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.reportes_app_actividadagentelog ALTER COLUMN id SET DEFAULT nextval('public.reportes_app_actividadagentelog_id_seq'::regclass);


--
-- TOC entry 4142 (class 2604 OID 18177)
-- Name: reportes_app_llamadalog id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.reportes_app_llamadalog ALTER COLUMN id SET DEFAULT nextval('public.reportes_app_llamadalog_id_seq'::regclass);


--
-- TOC entry 4154 (class 2604 OID 18221)
-- Name: reportes_app_transferenciaaencuestalog id; Type: DEFAULT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.reportes_app_transferenciaaencuestalog ALTER COLUMN id SET DEFAULT nextval('public.reportes_app_transferenciaaencuestalog_id_seq'::regclass);


--
-- TOC entry 4235 (class 2606 OID 17233)
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- TOC entry 4240 (class 2606 OID 16458)
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- TOC entry 4243 (class 2606 OID 16437)
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4237 (class 2606 OID 16427)
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- TOC entry 4230 (class 2606 OID 16444)
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- TOC entry 4232 (class 2606 OID 16419)
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- TOC entry 4405 (class 2606 OID 17218)
-- Name: authtoken_token authtoken_token_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_pkey PRIMARY KEY (key);


--
-- TOC entry 4407 (class 2606 OID 17220)
-- Name: authtoken_token authtoken_token_user_id_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_key UNIQUE (user_id);


--
-- TOC entry 4427 (class 2606 OID 17370)
-- Name: configuracion_telefonia_app_opciondestino configuracion_telefonia__destino_anterior_id_valo_78f24331_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_opciondestino
    ADD CONSTRAINT configuracion_telefonia__destino_anterior_id_valo_78f24331_uniq UNIQUE (destino_anterior_id, valor);


--
-- TOC entry 4439 (class 2606 OID 17366)
-- Name: configuracion_telefonia_app_patrondediscado configuracion_telefonia__orden_ruta_saliente_id_991d147d_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_patrondediscado
    ADD CONSTRAINT configuracion_telefonia__orden_ruta_saliente_id_991d147d_uniq UNIQUE (orden, ruta_saliente_id);


--
-- TOC entry 4433 (class 2606 OID 17368)
-- Name: configuracion_telefonia_app_ordentroncal configuracion_telefonia__orden_ruta_saliente_id_e5100a3b_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ordentroncal
    ADD CONSTRAINT configuracion_telefonia__orden_ruta_saliente_id_e5100a3b_uniq UNIQUE (orden, ruta_saliente_id);


--
-- TOC entry 4409 (class 2606 OID 17565)
-- Name: configuracion_telefonia_app_destinoentrante configuracion_telefonia__tipo_object_id_04593ce3_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_destinoentrante
    ADD CONSTRAINT configuracion_telefonia__tipo_object_id_04593ce3_uniq UNIQUE (tipo, object_id);


--
-- TOC entry 4504 (class 2606 OID 17626)
-- Name: configuracion_telefonia_app_amdconf configuracion_telefonia_app_amdconf_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_amdconf
    ADD CONSTRAINT configuracion_telefonia_app_amdconf_pkey PRIMARY KEY (id);


--
-- TOC entry 4508 (class 2606 OID 17642)
-- Name: configuracion_telefonia_app_audiosasteriskconf configuracion_telefonia_app_audiosasteriskconf_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_audiosasteriskconf
    ADD CONSTRAINT configuracion_telefonia_app_audiosasteriskconf_pkey PRIMARY KEY (id);


--
-- TOC entry 4412 (class 2606 OID 17248)
-- Name: configuracion_telefonia_app_destinoentrante configuracion_telefonia_app_destinoentrante_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_destinoentrante
    ADD CONSTRAINT configuracion_telefonia_app_destinoentrante_pkey PRIMARY KEY (id);


--
-- TOC entry 4487 (class 2606 OID 17577)
-- Name: configuracion_telefonia_app_destinopersonalizado configuracion_telefonia_app_destinoperso_custom_destination_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_destinopersonalizado
    ADD CONSTRAINT configuracion_telefonia_app_destinoperso_custom_destination_key UNIQUE (custom_destination);


--
-- TOC entry 4489 (class 2606 OID 17575)
-- Name: configuracion_telefonia_app_destinopersonalizado configuracion_telefonia_app_destinopersonalizado_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_destinopersonalizado
    ADD CONSTRAINT configuracion_telefonia_app_destinopersonalizado_nombre_key UNIQUE (nombre);


--
-- TOC entry 4491 (class 2606 OID 17573)
-- Name: configuracion_telefonia_app_destinopersonalizado configuracion_telefonia_app_destinopersonalizado_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_destinopersonalizado
    ADD CONSTRAINT configuracion_telefonia_app_destinopersonalizado_pkey PRIMARY KEY (id);


--
-- TOC entry 4506 (class 2606 OID 17634)
-- Name: configuracion_telefonia_app_esquemagrabaciones configuracion_telefonia_app_esquemagrabaciones_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_esquemagrabaciones
    ADD CONSTRAINT configuracion_telefonia_app_esquemagrabaciones_pkey PRIMARY KEY (id);


--
-- TOC entry 4415 (class 2606 OID 17260)
-- Name: configuracion_telefonia_app_grupohorario configuracion_telefonia_app_grupohorario_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_grupohorario
    ADD CONSTRAINT configuracion_telefonia_app_grupohorario_nombre_key UNIQUE (nombre);


--
-- TOC entry 4417 (class 2606 OID 17258)
-- Name: configuracion_telefonia_app_grupohorario configuracion_telefonia_app_grupohorario_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_grupohorario
    ADD CONSTRAINT configuracion_telefonia_app_grupohorario_pkey PRIMARY KEY (id);


--
-- TOC entry 4474 (class 2606 OID 17458)
-- Name: configuracion_telefonia_app_hangup configuracion_telefonia_app_hangup_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_hangup
    ADD CONSTRAINT configuracion_telefonia_app_hangup_pkey PRIMARY KEY (id);


--
-- TOC entry 4481 (class 2606 OID 17556)
-- Name: configuracion_telefonia_app_identificadorcliente configuracion_telefonia_app_identificadorcliente_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_identificadorcliente
    ADD CONSTRAINT configuracion_telefonia_app_identificadorcliente_nombre_key UNIQUE (nombre);


--
-- TOC entry 4483 (class 2606 OID 17554)
-- Name: configuracion_telefonia_app_identificadorcliente configuracion_telefonia_app_identificadorcliente_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_identificadorcliente
    ADD CONSTRAINT configuracion_telefonia_app_identificadorcliente_pkey PRIMARY KEY (id);


--
-- TOC entry 4422 (class 2606 OID 17273)
-- Name: configuracion_telefonia_app_ivr configuracion_telefonia_app_ivr_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ivr
    ADD CONSTRAINT configuracion_telefonia_app_ivr_nombre_key UNIQUE (nombre);


--
-- TOC entry 4424 (class 2606 OID 17271)
-- Name: configuracion_telefonia_app_ivr configuracion_telefonia_app_ivr_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ivr
    ADD CONSTRAINT configuracion_telefonia_app_ivr_pkey PRIMARY KEY (id);


--
-- TOC entry 4494 (class 2606 OID 17591)
-- Name: configuracion_telefonia_app_musicadeespera configuracion_telefonia_app_musicadeespera_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_musicadeespera
    ADD CONSTRAINT configuracion_telefonia_app_musicadeespera_nombre_key UNIQUE (nombre);


--
-- TOC entry 4496 (class 2606 OID 17589)
-- Name: configuracion_telefonia_app_musicadeespera configuracion_telefonia_app_musicadeespera_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_musicadeespera
    ADD CONSTRAINT configuracion_telefonia_app_musicadeespera_pkey PRIMARY KEY (id);


--
-- TOC entry 4431 (class 2606 OID 17281)
-- Name: configuracion_telefonia_app_opciondestino configuracion_telefonia_app_opciondestino_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_opciondestino
    ADD CONSTRAINT configuracion_telefonia_app_opciondestino_pkey PRIMARY KEY (id);


--
-- TOC entry 4436 (class 2606 OID 17290)
-- Name: configuracion_telefonia_app_ordentroncal configuracion_telefonia_app_ordentroncal_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ordentroncal
    ADD CONSTRAINT configuracion_telefonia_app_ordentroncal_pkey PRIMARY KEY (id);


--
-- TOC entry 4442 (class 2606 OID 17299)
-- Name: configuracion_telefonia_app_patrondediscado configuracion_telefonia_app_patrondediscado_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_patrondediscado
    ADD CONSTRAINT configuracion_telefonia_app_patrondediscado_pkey PRIMARY KEY (id);


--
-- TOC entry 4500 (class 2606 OID 17601)
-- Name: configuracion_telefonia_app_playlist configuracion_telefonia_app_playlist_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_playlist
    ADD CONSTRAINT configuracion_telefonia_app_playlist_nombre_key UNIQUE (nombre);


--
-- TOC entry 4502 (class 2606 OID 17599)
-- Name: configuracion_telefonia_app_playlist configuracion_telefonia_app_playlist_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_playlist
    ADD CONSTRAINT configuracion_telefonia_app_playlist_pkey PRIMARY KEY (id);


--
-- TOC entry 4446 (class 2606 OID 17310)
-- Name: configuracion_telefonia_app_rutaentrante configuracion_telefonia_app_rutaentrante_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_rutaentrante
    ADD CONSTRAINT configuracion_telefonia_app_rutaentrante_nombre_key UNIQUE (nombre);


--
-- TOC entry 4448 (class 2606 OID 17308)
-- Name: configuracion_telefonia_app_rutaentrante configuracion_telefonia_app_rutaentrante_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_rutaentrante
    ADD CONSTRAINT configuracion_telefonia_app_rutaentrante_pkey PRIMARY KEY (id);


--
-- TOC entry 4451 (class 2606 OID 17312)
-- Name: configuracion_telefonia_app_rutaentrante configuracion_telefonia_app_rutaentrante_telefono_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_rutaentrante
    ADD CONSTRAINT configuracion_telefonia_app_rutaentrante_telefono_key UNIQUE (telefono);


--
-- TOC entry 4454 (class 2606 OID 17326)
-- Name: configuracion_telefonia_app_rutasaliente configuracion_telefonia_app_rutasaliente_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_rutasaliente
    ADD CONSTRAINT configuracion_telefonia_app_rutasaliente_nombre_key UNIQUE (nombre);


--
-- TOC entry 4456 (class 2606 OID 17542)
-- Name: configuracion_telefonia_app_rutasaliente configuracion_telefonia_app_rutasaliente_orden_d65178fe_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_rutasaliente
    ADD CONSTRAINT configuracion_telefonia_app_rutasaliente_orden_d65178fe_uniq UNIQUE (orden);


--
-- TOC entry 4458 (class 2606 OID 17324)
-- Name: configuracion_telefonia_app_rutasaliente configuracion_telefonia_app_rutasaliente_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_rutasaliente
    ADD CONSTRAINT configuracion_telefonia_app_rutasaliente_pkey PRIMARY KEY (id);


--
-- TOC entry 4461 (class 2606 OID 17340)
-- Name: configuracion_telefonia_app_troncalsip configuracion_telefonia_app_troncalsip_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_troncalsip
    ADD CONSTRAINT configuracion_telefonia_app_troncalsip_nombre_key UNIQUE (nombre);


--
-- TOC entry 4463 (class 2606 OID 17338)
-- Name: configuracion_telefonia_app_troncalsip configuracion_telefonia_app_troncalsip_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_troncalsip
    ADD CONSTRAINT configuracion_telefonia_app_troncalsip_pkey PRIMARY KEY (id);


--
-- TOC entry 4467 (class 2606 OID 17350)
-- Name: configuracion_telefonia_app_validacionfechahora configuracion_telefonia_app_validacionfechahora_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_validacionfechahora
    ADD CONSTRAINT configuracion_telefonia_app_validacionfechahora_nombre_key UNIQUE (nombre);


--
-- TOC entry 4469 (class 2606 OID 17348)
-- Name: configuracion_telefonia_app_validacionfechahora configuracion_telefonia_app_validacionfechahora_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_validacionfechahora
    ADD CONSTRAINT configuracion_telefonia_app_validacionfechahora_pkey PRIMARY KEY (id);


--
-- TOC entry 4472 (class 2606 OID 17364)
-- Name: configuracion_telefonia_app_validaciontiempo configuracion_telefonia_app_validaciontiempo_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_validaciontiempo
    ADD CONSTRAINT configuracion_telefonia_app_validaciontiempo_pkey PRIMARY KEY (id);


--
-- TOC entry 4511 (class 2606 OID 17655)
-- Name: constance_config constance_config_key_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.constance_config
    ADD CONSTRAINT constance_config_key_key UNIQUE (key);


--
-- TOC entry 4513 (class 2606 OID 17653)
-- Name: constance_config constance_config_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.constance_config
    ADD CONSTRAINT constance_config_pkey PRIMARY KEY (id);


--
-- TOC entry 4515 (class 2606 OID 17667)
-- Name: defender_accessattempt defender_accessattempt_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.defender_accessattempt
    ADD CONSTRAINT defender_accessattempt_pkey PRIMARY KEY (id);


--
-- TOC entry 4401 (class 2606 OID 17201)
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- TOC entry 4225 (class 2606 OID 16411)
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- TOC entry 4227 (class 2606 OID 16409)
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- TOC entry 4223 (class 2606 OID 16401)
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- TOC entry 4623 (class 2606 OID 18237)
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- TOC entry 4519 (class 2606 OID 17678)
-- Name: easyaudit_crudevent easyaudit_crudevent_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.easyaudit_crudevent
    ADD CONSTRAINT easyaudit_crudevent_pkey PRIMARY KEY (id);


--
-- TOC entry 4522 (class 2606 OID 17686)
-- Name: easyaudit_loginevent easyaudit_loginevent_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.easyaudit_loginevent
    ADD CONSTRAINT easyaudit_loginevent_pkey PRIMARY KEY (id);


--
-- TOC entry 4529 (class 2606 OID 17726)
-- Name: easyaudit_requestevent easyaudit_requestevent_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.easyaudit_requestevent
    ADD CONSTRAINT easyaudit_requestevent_pkey PRIMARY KEY (id);


--
-- TOC entry 4626 (class 2606 OID 18340)
-- Name: form_app_encuesta form_app_encuesta_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.form_app_encuesta
    ADD CONSTRAINT form_app_encuesta_pkey PRIMARY KEY (id);


--
-- TOC entry 4628 (class 2606 OID 18351)
-- Name: form_app_formulario form_app_formulario_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.form_app_formulario
    ADD CONSTRAINT form_app_formulario_pkey PRIMARY KEY (id);


--
-- TOC entry 4262 (class 2606 OID 16876)
-- Name: ominicontacto_app_actuacionvigente ominicontacto_app_actuacionvigente_campana_id_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_actuacionvigente
    ADD CONSTRAINT ominicontacto_app_actuacionvigente_campana_id_key UNIQUE (campana_id);


--
-- TOC entry 4264 (class 2606 OID 16497)
-- Name: ominicontacto_app_actuacionvigente ominicontacto_app_actuacionvigente_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_actuacionvigente
    ADD CONSTRAINT ominicontacto_app_actuacionvigente_pkey PRIMARY KEY (id);


--
-- TOC entry 4269 (class 2606 OID 16521)
-- Name: ominicontacto_app_agendacontacto ominicontacto_app_agendacontacto_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agendacontacto
    ADD CONSTRAINT ominicontacto_app_agendacontacto_pkey PRIMARY KEY (id);


--
-- TOC entry 4541 (class 2606 OID 17800)
-- Name: ominicontacto_app_agenteensistemaexterno ominicontacto_app_agente_sistema_externo_id_agent_90630bef_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteensistemaexterno
    ADD CONSTRAINT ominicontacto_app_agente_sistema_externo_id_agent_90630bef_uniq UNIQUE (sistema_externo_id, agente_id);


--
-- TOC entry 4543 (class 2606 OID 17798)
-- Name: ominicontacto_app_agenteensistemaexterno ominicontacto_app_agente_sistema_externo_id_id_ex_866c1341_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteensistemaexterno
    ADD CONSTRAINT ominicontacto_app_agente_sistema_externo_id_id_ex_866c1341_uniq UNIQUE (sistema_externo_id, id_externo_agente);


--
-- TOC entry 4271 (class 2606 OID 16533)
-- Name: ominicontacto_app_agenteencontacto ominicontacto_app_agenteencontacto_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteencontacto
    ADD CONSTRAINT ominicontacto_app_agenteencontacto_pkey PRIMARY KEY (id);


--
-- TOC entry 4547 (class 2606 OID 17796)
-- Name: ominicontacto_app_agenteensistemaexterno ominicontacto_app_agenteensistemaexterno_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteensistemaexterno
    ADD CONSTRAINT ominicontacto_app_agenteensistemaexterno_pkey PRIMARY KEY (id);


--
-- TOC entry 4274 (class 2606 OID 16542)
-- Name: ominicontacto_app_agenteprofile ominicontacto_app_agenteprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteprofile
    ADD CONSTRAINT ominicontacto_app_agenteprofile_pkey PRIMARY KEY (id);


--
-- TOC entry 4277 (class 2606 OID 16544)
-- Name: ominicontacto_app_agenteprofile ominicontacto_app_agenteprofile_sip_extension_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteprofile
    ADD CONSTRAINT ominicontacto_app_agenteprofile_sip_extension_key UNIQUE (sip_extension);


--
-- TOC entry 4279 (class 2606 OID 16874)
-- Name: ominicontacto_app_agenteprofile ominicontacto_app_agenteprofile_user_id_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteprofile
    ADD CONSTRAINT ominicontacto_app_agenteprofile_user_id_key UNIQUE (user_id);


--
-- TOC entry 4282 (class 2606 OID 16554)
-- Name: ominicontacto_app_archivodeaudio ominicontacto_app_archivodeaudio_descripcion_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_archivodeaudio
    ADD CONSTRAINT ominicontacto_app_archivodeaudio_descripcion_key UNIQUE (descripcion);


--
-- TOC entry 4284 (class 2606 OID 16552)
-- Name: ominicontacto_app_archivodeaudio ominicontacto_app_archivodeaudio_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_archivodeaudio
    ADD CONSTRAINT ominicontacto_app_archivodeaudio_pkey PRIMARY KEY (id);


--
-- TOC entry 4555 (class 2606 OID 17930)
-- Name: ominicontacto_app_auditoriacalificacion ominicontacto_app_auditoriacalificacion_calificacion_id_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_auditoriacalificacion
    ADD CONSTRAINT ominicontacto_app_auditoriacalificacion_calificacion_id_key UNIQUE (calificacion_id);


--
-- TOC entry 4557 (class 2606 OID 17928)
-- Name: ominicontacto_app_auditoriacalificacion ominicontacto_app_auditoriacalificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_auditoriacalificacion
    ADD CONSTRAINT ominicontacto_app_auditoriacalificacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4594 (class 2606 OID 18149)
-- Name: ominicontacto_app_autenticacionsitioexterno ominicontacto_app_autenticacionsitioexterno_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_autenticacionsitioexterno
    ADD CONSTRAINT ominicontacto_app_autenticacionsitioexterno_nombre_key UNIQUE (nombre);


--
-- TOC entry 4596 (class 2606 OID 18147)
-- Name: ominicontacto_app_autenticacionsitioexterno ominicontacto_app_autenticacionsitioexterno_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_autenticacionsitioexterno
    ADD CONSTRAINT ominicontacto_app_autenticacionsitioexterno_pkey PRIMARY KEY (id);


--
-- TOC entry 4286 (class 2606 OID 16566)
-- Name: ominicontacto_app_blacklist ominicontacto_app_backlist_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_blacklist
    ADD CONSTRAINT ominicontacto_app_backlist_pkey PRIMARY KEY (id);


--
-- TOC entry 4289 (class 2606 OID 17832)
-- Name: ominicontacto_app_basedatoscontacto ominicontacto_app_basedatoscontacto_nombre_6cf964df_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_basedatoscontacto
    ADD CONSTRAINT ominicontacto_app_basedatoscontacto_nombre_6cf964df_uniq UNIQUE (nombre);


--
-- TOC entry 4291 (class 2606 OID 16579)
-- Name: ominicontacto_app_basedatoscontacto ominicontacto_app_basedatoscontacto_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_basedatoscontacto
    ADD CONSTRAINT ominicontacto_app_basedatoscontacto_pkey PRIMARY KEY (id);


--
-- TOC entry 4298 (class 2606 OID 16590)
-- Name: ominicontacto_app_calificacioncliente ominicontacto_app_calificacioncliente_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_calificacioncliente
    ADD CONSTRAINT ominicontacto_app_calificacioncliente_pkey PRIMARY KEY (id);


--
-- TOC entry 4394 (class 2606 OID 17115)
-- Name: ominicontacto_app_campana_supervisors ominicontacto_app_campan_campana_id_user_id_abb0a2c5_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana_supervisors
    ADD CONSTRAINT ominicontacto_app_campan_campana_id_user_id_abb0a2c5_uniq UNIQUE (campana_id, user_id);


--
-- TOC entry 4302 (class 2606 OID 16605)
-- Name: ominicontacto_app_campana ominicontacto_app_campana_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana
    ADD CONSTRAINT ominicontacto_app_campana_nombre_key UNIQUE (nombre);


--
-- TOC entry 4305 (class 2606 OID 16603)
-- Name: ominicontacto_app_campana ominicontacto_app_campana_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana
    ADD CONSTRAINT ominicontacto_app_campana_pkey PRIMARY KEY (id);


--
-- TOC entry 4397 (class 2606 OID 16864)
-- Name: ominicontacto_app_campana_supervisors ominicontacto_app_campana_supervisors_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana_supervisors
    ADD CONSTRAINT ominicontacto_app_campana_supervisors_pkey PRIMARY KEY (id);


--
-- TOC entry 4311 (class 2606 OID 16613)
-- Name: ominicontacto_app_chat ominicontacto_app_chat_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_chat
    ADD CONSTRAINT ominicontacto_app_chat_pkey PRIMARY KEY (id);


--
-- TOC entry 4549 (class 2606 OID 17841)
-- Name: ominicontacto_app_clientewebphoneprofile ominicontacto_app_clientewebphoneprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_clientewebphoneprofile
    ADD CONSTRAINT ominicontacto_app_clientewebphoneprofile_pkey PRIMARY KEY (id);


--
-- TOC entry 4551 (class 2606 OID 17843)
-- Name: ominicontacto_app_clientewebphoneprofile ominicontacto_app_clientewebphoneprofile_sip_extension_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_clientewebphoneprofile
    ADD CONSTRAINT ominicontacto_app_clientewebphoneprofile_sip_extension_key UNIQUE (sip_extension);


--
-- TOC entry 4553 (class 2606 OID 17846)
-- Name: ominicontacto_app_clientewebphoneprofile ominicontacto_app_clientewebphoneprofile_user_id_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_clientewebphoneprofile
    ADD CONSTRAINT ominicontacto_app_clientewebphoneprofile_user_id_key UNIQUE (user_id);


--
-- TOC entry 4569 (class 2606 OID 18000)
-- Name: ominicontacto_app_configuraciondeagentesdecampana ominicontacto_app_configuraciondeagentesdecampan_campana_id_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_configuraciondeagentesdecampana
    ADD CONSTRAINT ominicontacto_app_configuraciondeagentesdecampan_campana_id_key UNIQUE (campana_id);


--
-- TOC entry 4571 (class 2606 OID 17998)
-- Name: ominicontacto_app_configuraciondeagentesdecampana ominicontacto_app_configuraciondeagentesdecampana_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_configuraciondeagentesdecampana
    ADD CONSTRAINT ominicontacto_app_configuraciondeagentesdecampana_pkey PRIMARY KEY (id);


--
-- TOC entry 4591 (class 2606 OID 18093)
-- Name: ominicontacto_app_configuraciondepausa ominicontacto_app_configuraciondepausa_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_configuraciondepausa
    ADD CONSTRAINT ominicontacto_app_configuraciondepausa_pkey PRIMARY KEY (id);


--
-- TOC entry 4587 (class 2606 OID 18085)
-- Name: ominicontacto_app_conjuntodepausa ominicontacto_app_conjuntodepausa_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_conjuntodepausa
    ADD CONSTRAINT ominicontacto_app_conjuntodepausa_pkey PRIMARY KEY (id);


--
-- TOC entry 4315 (class 2606 OID 16624)
-- Name: ominicontacto_app_contacto ominicontacto_app_contacto_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contacto
    ADD CONSTRAINT ominicontacto_app_contacto_pkey PRIMARY KEY (id);


--
-- TOC entry 4560 (class 2606 OID 17949)
-- Name: ominicontacto_app_contactoblacklist ominicontacto_app_contactoblacklist_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contactoblacklist
    ADD CONSTRAINT ominicontacto_app_contactoblacklist_pkey PRIMARY KEY (id);


--
-- TOC entry 4563 (class 2606 OID 18066)
-- Name: ominicontacto_app_contactoblacklist ominicontacto_app_contactoblacklist_telefono_a1dfe877_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contactoblacklist
    ADD CONSTRAINT ominicontacto_app_contactoblacklist_telefono_a1dfe877_uniq UNIQUE (telefono);


--
-- TOC entry 4585 (class 2606 OID 18047)
-- Name: ominicontacto_app_contactolistarapida ominicontacto_app_contactolistarapida_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contactolistarapida
    ADD CONSTRAINT ominicontacto_app_contactolistarapida_pkey PRIMARY KEY (id);


--
-- TOC entry 4317 (class 2606 OID 16880)
-- Name: ominicontacto_app_fieldformulario ominicontacto_app_fieldf_orden_formulario_id_6218007e_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_fieldformulario
    ADD CONSTRAINT ominicontacto_app_fieldf_orden_formulario_id_6218007e_uniq UNIQUE (orden, formulario_id);


--
-- TOC entry 4320 (class 2606 OID 16654)
-- Name: ominicontacto_app_fieldformulario ominicontacto_app_fieldformulario_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_fieldformulario
    ADD CONSTRAINT ominicontacto_app_fieldformulario_pkey PRIMARY KEY (id);


--
-- TOC entry 4322 (class 2606 OID 16665)
-- Name: ominicontacto_app_formulario ominicontacto_app_formulario_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_formulario
    ADD CONSTRAINT ominicontacto_app_formulario_pkey PRIMARY KEY (id);


--
-- TOC entry 4324 (class 2606 OID 16688)
-- Name: ominicontacto_app_grabacion_marca ominicontacto_app_grabacion_marca_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_grabacion_marca
    ADD CONSTRAINT ominicontacto_app_grabacion_marca_pkey PRIMARY KEY (id);


--
-- TOC entry 4328 (class 2606 OID 17829)
-- Name: ominicontacto_app_grupo ominicontacto_app_grupo_nombre_09c6de5a_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_grupo
    ADD CONSTRAINT ominicontacto_app_grupo_nombre_09c6de5a_uniq UNIQUE (nombre);


--
-- TOC entry 4330 (class 2606 OID 16697)
-- Name: ominicontacto_app_grupo ominicontacto_app_grupo_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_grupo
    ADD CONSTRAINT ominicontacto_app_grupo_pkey PRIMARY KEY (id);


--
-- TOC entry 4339 (class 2606 OID 16708)
-- Name: ominicontacto_app_historicalcalificacioncliente ominicontacto_app_historicalcalificacioncliente_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_historicalcalificacioncliente
    ADD CONSTRAINT ominicontacto_app_historicalcalificacioncliente_pkey PRIMARY KEY (history_id);


--
-- TOC entry 4577 (class 2606 OID 18017)
-- Name: ominicontacto_app_historicalrespuestaformulariogestion ominicontacto_app_historicalrespuestaformulariogestion_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_historicalrespuestaformulariogestion
    ADD CONSTRAINT ominicontacto_app_historicalrespuestaformulariogestion_pkey PRIMARY KEY (history_id);


--
-- TOC entry 4580 (class 2606 OID 18039)
-- Name: ominicontacto_app_listasrapidas ominicontacto_app_listasrapidas_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_listasrapidas
    ADD CONSTRAINT ominicontacto_app_listasrapidas_nombre_key UNIQUE (nombre);


--
-- TOC entry 4582 (class 2606 OID 18037)
-- Name: ominicontacto_app_listasrapidas ominicontacto_app_listasrapidas_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_listasrapidas
    ADD CONSTRAINT ominicontacto_app_listasrapidas_pkey PRIMARY KEY (id);


--
-- TOC entry 4342 (class 2606 OID 16719)
-- Name: ominicontacto_app_mensajechat ominicontacto_app_mensajechat_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_mensajechat
    ADD CONSTRAINT ominicontacto_app_mensajechat_pkey PRIMARY KEY (id);


--
-- TOC entry 4346 (class 2606 OID 16752)
-- Name: ominicontacto_app_respuestaformulariogestion ominicontacto_app_metadatacliente_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_respuestaformulariogestion
    ADD CONSTRAINT ominicontacto_app_metadatacliente_pkey PRIMARY KEY (id);


--
-- TOC entry 4349 (class 2606 OID 16768)
-- Name: ominicontacto_app_nombrecalificacion ominicontacto_app_nombrecalificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_nombrecalificacion
    ADD CONSTRAINT ominicontacto_app_nombrecalificacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4353 (class 2606 OID 16776)
-- Name: ominicontacto_app_opcioncalificacion ominicontacto_app_opcioncalificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_opcioncalificacion
    ADD CONSTRAINT ominicontacto_app_opcioncalificacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4477 (class 2606 OID 17494)
-- Name: ominicontacto_app_parametroscrm ominicontacto_app_parametroscrm_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_parametroscrm
    ADD CONSTRAINT ominicontacto_app_parametroscrm_pkey PRIMARY KEY (id);


--
-- TOC entry 4356 (class 2606 OID 16794)
-- Name: ominicontacto_app_pausa ominicontacto_app_pausa_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_pausa
    ADD CONSTRAINT ominicontacto_app_pausa_nombre_key UNIQUE (nombre);


--
-- TOC entry 4358 (class 2606 OID 16792)
-- Name: ominicontacto_app_pausa ominicontacto_app_pausa_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_pausa
    ADD CONSTRAINT ominicontacto_app_pausa_pkey PRIMARY KEY (id);


--
-- TOC entry 4565 (class 2606 OID 17978)
-- Name: ominicontacto_app_reglaincidenciaporcalificacion ominicontacto_app_reglaincidenciapor_opcion_calificacion_id_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_reglaincidenciaporcalificacion
    ADD CONSTRAINT ominicontacto_app_reglaincidenciapor_opcion_calificacion_id_key UNIQUE (opcion_calificacion_id);


--
-- TOC entry 4567 (class 2606 OID 17976)
-- Name: ominicontacto_app_reglaincidenciaporcalificacion ominicontacto_app_reglaincidenciaporcalificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_reglaincidenciaporcalificacion
    ADD CONSTRAINT ominicontacto_app_reglaincidenciaporcalificacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4380 (class 2606 OID 16826)
-- Name: ominicontacto_app_reglasincidencia ominicontacto_app_reglasincidencia_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_reglasincidencia
    ADD CONSTRAINT ominicontacto_app_reglasincidencia_pkey PRIMARY KEY (id);


--
-- TOC entry 4537 (class 2606 OID 17787)
-- Name: ominicontacto_app_sistemaexterno ominicontacto_app_sistemaexterno_nombre_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_sistemaexterno
    ADD CONSTRAINT ominicontacto_app_sistemaexterno_nombre_key UNIQUE (nombre);


--
-- TOC entry 4539 (class 2606 OID 17785)
-- Name: ominicontacto_app_sistemaexterno ominicontacto_app_sistemaexterno_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_sistemaexterno
    ADD CONSTRAINT ominicontacto_app_sistemaexterno_pkey PRIMARY KEY (id);


--
-- TOC entry 4384 (class 2606 OID 18117)
-- Name: ominicontacto_app_sitioexterno ominicontacto_app_sitioexterno_nombre_f6a98fa8_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_sitioexterno
    ADD CONSTRAINT ominicontacto_app_sitioexterno_nombre_f6a98fa8_uniq UNIQUE (nombre);


--
-- TOC entry 4386 (class 2606 OID 16834)
-- Name: ominicontacto_app_sitioexterno ominicontacto_app_sitioexterno_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_sitioexterno
    ADD CONSTRAINT ominicontacto_app_sitioexterno_pkey PRIMARY KEY (id);


--
-- TOC entry 4388 (class 2606 OID 16842)
-- Name: ominicontacto_app_supervisorprofile ominicontacto_app_supervisorprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_supervisorprofile
    ADD CONSTRAINT ominicontacto_app_supervisorprofile_pkey PRIMARY KEY (id);


--
-- TOC entry 4390 (class 2606 OID 16844)
-- Name: ominicontacto_app_supervisorprofile ominicontacto_app_supervisorprofile_sip_extension_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_supervisorprofile
    ADD CONSTRAINT ominicontacto_app_supervisorprofile_sip_extension_key UNIQUE (sip_extension);


--
-- TOC entry 4392 (class 2606 OID 16846)
-- Name: ominicontacto_app_supervisorprofile ominicontacto_app_supervisorprofile_user_id_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_supervisorprofile
    ADD CONSTRAINT ominicontacto_app_supervisorprofile_user_id_key UNIQUE (user_id);


--
-- TOC entry 4251 (class 2606 OID 16481)
-- Name: ominicontacto_app_user_groups ominicontacto_app_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_groups
    ADD CONSTRAINT ominicontacto_app_user_groups_pkey PRIMARY KEY (id);


--
-- TOC entry 4254 (class 2606 OID 16893)
-- Name: ominicontacto_app_user_groups ominicontacto_app_user_groups_user_id_group_id_9ea58fa3_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_groups
    ADD CONSTRAINT ominicontacto_app_user_groups_user_id_group_id_9ea58fa3_uniq UNIQUE (user_id, group_id);


--
-- TOC entry 4245 (class 2606 OID 16471)
-- Name: ominicontacto_app_user ominicontacto_app_user_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user
    ADD CONSTRAINT ominicontacto_app_user_pkey PRIMARY KEY (id);


--
-- TOC entry 4256 (class 2606 OID 16907)
-- Name: ominicontacto_app_user_user_permissions ominicontacto_app_user_u_user_id_permission_id_c7a8cf96_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_user_permissions
    ADD CONSTRAINT ominicontacto_app_user_u_user_id_permission_id_c7a8cf96_uniq UNIQUE (user_id, permission_id);


--
-- TOC entry 4259 (class 2606 OID 16489)
-- Name: ominicontacto_app_user_user_permissions ominicontacto_app_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_user_permissions
    ADD CONSTRAINT ominicontacto_app_user_user_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4248 (class 2606 OID 17860)
-- Name: ominicontacto_app_user ominicontacto_app_user_username_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user
    ADD CONSTRAINT ominicontacto_app_user_username_key UNIQUE (username);


--
-- TOC entry 4612 (class 2606 OID 18197)
-- Name: queue_log queue_log_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_log
    ADD CONSTRAINT queue_log_pkey PRIMARY KEY (id);


--
-- TOC entry 4373 (class 2606 OID 16816)
-- Name: queue_member_table queue_member_table_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_member_table
    ADD CONSTRAINT queue_member_table_pkey PRIMARY KEY (id);


--
-- TOC entry 4377 (class 2606 OID 16878)
-- Name: queue_member_table queue_member_table_queue_name_member_id_1e319083_uniq; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_member_table
    ADD CONSTRAINT queue_member_table_queue_name_member_id_1e319083_uniq UNIQUE (queue_name, member_id);


--
-- TOC entry 4364 (class 2606 OID 16805)
-- Name: queue_table queue_table_campana_id_key; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_campana_id_key UNIQUE (campana_id);


--
-- TOC entry 4370 (class 2606 OID 16803)
-- Name: queue_table queue_table_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_pkey PRIMARY KEY (name);


--
-- TOC entry 4599 (class 2606 OID 18171)
-- Name: reportes_app_actividadagentelog reportes_app_actividadagentelog_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.reportes_app_actividadagentelog
    ADD CONSTRAINT reportes_app_actividadagentelog_pkey PRIMARY KEY (id);


--
-- TOC entry 4609 (class 2606 OID 18179)
-- Name: reportes_app_llamadalog reportes_app_llamadalog_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.reportes_app_llamadalog
    ADD CONSTRAINT reportes_app_llamadalog_pkey PRIMARY KEY (id);


--
-- TOC entry 4619 (class 2606 OID 18223)
-- Name: reportes_app_transferenciaaencuestalog reportes_app_transferenciaaencuestalog_pkey; Type: CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.reportes_app_transferenciaaencuestalog
    ADD CONSTRAINT reportes_app_transferenciaaencuestalog_pkey PRIMARY KEY (id);


--
-- TOC entry 4233 (class 1259 OID 17234)
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- TOC entry 4238 (class 1259 OID 16459)
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- TOC entry 4241 (class 1259 OID 16460)
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- TOC entry 4228 (class 1259 OID 16445)
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- TOC entry 4403 (class 1259 OID 17226)
-- Name: authtoken_token_key_10f0b77e_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX authtoken_token_key_10f0b77e_like ON public.authtoken_token USING btree (key varchar_pattern_ops);


--
-- TOC entry 4292 (class 1259 OID 17965)
-- Name: calif_cliente_callid_index; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX calif_cliente_callid_index ON public.ominicontacto_app_calificacioncliente USING btree (callid);


--
-- TOC entry 4484 (class 1259 OID 17579)
-- Name: configuracion_telefonia__custom_destination_de84e134_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia__custom_destination_de84e134_like ON public.configuracion_telefonia_app_destinopersonalizado USING btree (custom_destination varchar_pattern_ops);


--
-- TOC entry 4485 (class 1259 OID 17578)
-- Name: configuracion_telefonia__nombre_110ace4f_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia__nombre_110ace4f_like ON public.configuracion_telefonia_app_destinopersonalizado USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4464 (class 1259 OID 17425)
-- Name: configuracion_telefonia__nombre_cd9329b7_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia__nombre_cd9329b7_like ON public.configuracion_telefonia_app_validacionfechahora USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4478 (class 1259 OID 17562)
-- Name: configuracion_telefonia__nombre_dac55234_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia__nombre_dac55234_like ON public.configuracion_telefonia_app_identificadorcliente USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4479 (class 1259 OID 17563)
-- Name: configuracion_telefonia_ap_audio_id_b57c0fee; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_ap_audio_id_b57c0fee ON public.configuracion_telefonia_app_identificadorcliente USING btree (audio_id);


--
-- TOC entry 4410 (class 1259 OID 17377)
-- Name: configuracion_telefonia_ap_content_type_id_8f3d2b4d; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_ap_content_type_id_8f3d2b4d ON public.configuracion_telefonia_app_destinoentrante USING btree (content_type_id);


--
-- TOC entry 4428 (class 1259 OID 17408)
-- Name: configuracion_telefonia_ap_destino_anterior_id_0996ab3b; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_ap_destino_anterior_id_0996ab3b ON public.configuracion_telefonia_app_opciondestino USING btree (destino_anterior_id);


--
-- TOC entry 4429 (class 1259 OID 17409)
-- Name: configuracion_telefonia_ap_destino_siguiente_id_5baf22fc; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_ap_destino_siguiente_id_5baf22fc ON public.configuracion_telefonia_app_opciondestino USING btree (destino_siguiente_id);


--
-- TOC entry 4465 (class 1259 OID 17426)
-- Name: configuracion_telefonia_ap_grupo_horario_id_2a6d57f1; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_ap_grupo_horario_id_2a6d57f1 ON public.configuracion_telefonia_app_validacionfechahora USING btree (grupo_horario_id);


--
-- TOC entry 4470 (class 1259 OID 17432)
-- Name: configuracion_telefonia_ap_grupo_horario_id_d708e8ee; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_ap_grupo_horario_id_d708e8ee ON public.configuracion_telefonia_app_validaciontiempo USING btree (grupo_horario_id);


--
-- TOC entry 4440 (class 1259 OID 17433)
-- Name: configuracion_telefonia_ap_ruta_saliente_id_7b111e0f; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_ap_ruta_saliente_id_7b111e0f ON public.configuracion_telefonia_app_patrondediscado USING btree (ruta_saliente_id);


--
-- TOC entry 4434 (class 1259 OID 17439)
-- Name: configuracion_telefonia_ap_ruta_saliente_id_bd46bea8; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_ap_ruta_saliente_id_bd46bea8 ON public.configuracion_telefonia_app_ordentroncal USING btree (ruta_saliente_id);


--
-- TOC entry 4413 (class 1259 OID 17378)
-- Name: configuracion_telefonia_app_grupohorario_nombre_33db5287_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_grupohorario_nombre_33db5287_like ON public.configuracion_telefonia_app_grupohorario USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4418 (class 1259 OID 17395)
-- Name: configuracion_telefonia_app_ivr_audio_principal_id_f765af13; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_ivr_audio_principal_id_f765af13 ON public.configuracion_telefonia_app_ivr USING btree (audio_principal_id);


--
-- TOC entry 4419 (class 1259 OID 17396)
-- Name: configuracion_telefonia_app_ivr_invalid_audio_id_260b2a2a; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_ivr_invalid_audio_id_260b2a2a ON public.configuracion_telefonia_app_ivr USING btree (invalid_audio_id);


--
-- TOC entry 4420 (class 1259 OID 17394)
-- Name: configuracion_telefonia_app_ivr_nombre_aa006c3e_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_ivr_nombre_aa006c3e_like ON public.configuracion_telefonia_app_ivr USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4425 (class 1259 OID 17397)
-- Name: configuracion_telefonia_app_ivr_time_out_audio_id_e2235eb3; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_ivr_time_out_audio_id_e2235eb3 ON public.configuracion_telefonia_app_ivr USING btree (time_out_audio_id);


--
-- TOC entry 4492 (class 1259 OID 17602)
-- Name: configuracion_telefonia_app_musicadeespera_nombre_928bcd5b_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_musicadeespera_nombre_928bcd5b_like ON public.configuracion_telefonia_app_musicadeespera USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4497 (class 1259 OID 17604)
-- Name: configuracion_telefonia_app_musicadeespera_playlist_id_9fb0431b; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_musicadeespera_playlist_id_9fb0431b ON public.configuracion_telefonia_app_musicadeespera USING btree (playlist_id);


--
-- TOC entry 4437 (class 1259 OID 17445)
-- Name: configuracion_telefonia_app_ordentroncal_troncal_id_edef8a14; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_ordentroncal_troncal_id_edef8a14 ON public.configuracion_telefonia_app_ordentroncal USING btree (troncal_id);


--
-- TOC entry 4498 (class 1259 OID 17603)
-- Name: configuracion_telefonia_app_playlist_nombre_23bb54e4_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_playlist_nombre_23bb54e4_like ON public.configuracion_telefonia_app_playlist USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4443 (class 1259 OID 17417)
-- Name: configuracion_telefonia_app_rutaentrante_destino_id_14fb9d9d; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_rutaentrante_destino_id_14fb9d9d ON public.configuracion_telefonia_app_rutaentrante USING btree (destino_id);


--
-- TOC entry 4444 (class 1259 OID 17415)
-- Name: configuracion_telefonia_app_rutaentrante_nombre_aae90e75_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_rutaentrante_nombre_aae90e75_like ON public.configuracion_telefonia_app_rutaentrante USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4449 (class 1259 OID 17416)
-- Name: configuracion_telefonia_app_rutaentrante_telefono_e01c4dea_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_rutaentrante_telefono_e01c4dea_like ON public.configuracion_telefonia_app_rutaentrante USING btree (telefono varchar_pattern_ops);


--
-- TOC entry 4452 (class 1259 OID 17418)
-- Name: configuracion_telefonia_app_rutasaliente_nombre_6e2a2b8e_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_rutasaliente_nombre_6e2a2b8e_like ON public.configuracion_telefonia_app_rutasaliente USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4459 (class 1259 OID 17419)
-- Name: configuracion_telefonia_app_troncalsip_nombre_8a4fa272_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX configuracion_telefonia_app_troncalsip_nombre_8a4fa272_like ON public.configuracion_telefonia_app_troncalsip USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4509 (class 1259 OID 17656)
-- Name: constance_config_key_baef3136_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX constance_config_key_baef3136_like ON public.constance_config USING btree (key varchar_pattern_ops);


--
-- TOC entry 4399 (class 1259 OID 17212)
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- TOC entry 4402 (class 1259 OID 17213)
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- TOC entry 4621 (class 1259 OID 18239)
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- TOC entry 4624 (class 1259 OID 18238)
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- TOC entry 4516 (class 1259 OID 17697)
-- Name: easyaudit_crudevent_content_type_id_618ed0c6; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_crudevent_content_type_id_618ed0c6 ON public.easyaudit_crudevent USING btree (content_type_id);


--
-- TOC entry 4517 (class 1259 OID 17767)
-- Name: easyaudit_crudevent_object_id_content_type_id_48e7e97f_idx; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_crudevent_object_id_content_type_id_48e7e97f_idx ON public.easyaudit_crudevent USING btree (object_id, content_type_id);


--
-- TOC entry 4520 (class 1259 OID 17698)
-- Name: easyaudit_crudevent_user_id_09177b54; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_crudevent_user_id_09177b54 ON public.easyaudit_crudevent USING btree (user_id);


--
-- TOC entry 4523 (class 1259 OID 17739)
-- Name: easyaudit_loginevent_remote_ip_52fb5c3c; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_loginevent_remote_ip_52fb5c3c ON public.easyaudit_loginevent USING btree (remote_ip);


--
-- TOC entry 4524 (class 1259 OID 17740)
-- Name: easyaudit_loginevent_remote_ip_52fb5c3c_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_loginevent_remote_ip_52fb5c3c_like ON public.easyaudit_loginevent USING btree (remote_ip varchar_pattern_ops);


--
-- TOC entry 4525 (class 1259 OID 17704)
-- Name: easyaudit_loginevent_user_id_f47fcbfb; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_loginevent_user_id_f47fcbfb ON public.easyaudit_loginevent USING btree (user_id);


--
-- TOC entry 4526 (class 1259 OID 17734)
-- Name: easyaudit_requestevent_method_83a0c884; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_requestevent_method_83a0c884 ON public.easyaudit_requestevent USING btree (method);


--
-- TOC entry 4527 (class 1259 OID 17735)
-- Name: easyaudit_requestevent_method_83a0c884_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_requestevent_method_83a0c884_like ON public.easyaudit_requestevent USING btree (method varchar_pattern_ops);


--
-- TOC entry 4530 (class 1259 OID 17736)
-- Name: easyaudit_requestevent_remote_ip_d43af9b2; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_requestevent_remote_ip_d43af9b2 ON public.easyaudit_requestevent USING btree (remote_ip);


--
-- TOC entry 4531 (class 1259 OID 17737)
-- Name: easyaudit_requestevent_remote_ip_d43af9b2_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_requestevent_remote_ip_d43af9b2_like ON public.easyaudit_requestevent USING btree (remote_ip varchar_pattern_ops);


--
-- TOC entry 4532 (class 1259 OID 17765)
-- Name: easyaudit_requestevent_url_37d1b8c4; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_requestevent_url_37d1b8c4 ON public.easyaudit_requestevent USING btree (url);


--
-- TOC entry 4533 (class 1259 OID 17766)
-- Name: easyaudit_requestevent_url_37d1b8c4_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_requestevent_url_37d1b8c4_like ON public.easyaudit_requestevent USING btree (url varchar_pattern_ops);


--
-- TOC entry 4534 (class 1259 OID 17738)
-- Name: easyaudit_requestevent_user_id_da412f45; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX easyaudit_requestevent_user_id_da412f45 ON public.easyaudit_requestevent USING btree (user_id);


--
-- TOC entry 4331 (class 1259 OID 18163)
-- Name: histcalifcli_hist_modified_idx; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX histcalifcli_hist_modified_idx ON public.ominicontacto_app_historicalcalificacioncliente USING btree (modified);


--
-- TOC entry 4332 (class 1259 OID 17963)
-- Name: history_date_index; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX history_date_index ON public.ominicontacto_app_historicalcalificacioncliente USING btree (history_date);


--
-- TOC entry 4572 (class 1259 OID 18135)
-- Name: histresp_hist_chg_reason_idx; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX histresp_hist_chg_reason_idx ON public.ominicontacto_app_historicalrespuestaformulariogestion USING btree (history_change_reason);


--
-- TOC entry 4293 (class 1259 OID 17941)
-- Name: ominicontac_fecha_4f98a8_idx; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontac_fecha_4f98a8_idx ON public.ominicontacto_app_calificacioncliente USING btree (fecha);


--
-- TOC entry 4265 (class 1259 OID 17161)
-- Name: ominicontacto_app_agendacontacto_agente_id_34ccaf4a; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_agendacontacto_agente_id_34ccaf4a ON public.ominicontacto_app_agendacontacto USING btree (agente_id);


--
-- TOC entry 4266 (class 1259 OID 17167)
-- Name: ominicontacto_app_agendacontacto_campana_id_364b62ec; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_agendacontacto_campana_id_364b62ec ON public.ominicontacto_app_agendacontacto USING btree (campana_id);


--
-- TOC entry 4267 (class 1259 OID 17173)
-- Name: ominicontacto_app_agendacontacto_contacto_id_81a823de; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_agendacontacto_contacto_id_81a823de ON public.ominicontacto_app_agendacontacto USING btree (contacto_id);


--
-- TOC entry 4544 (class 1259 OID 17812)
-- Name: ominicontacto_app_agenteen_sistema_externo_id_f6fba0d7; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_agenteen_sistema_externo_id_f6fba0d7 ON public.ominicontacto_app_agenteensistemaexterno USING btree (sistema_externo_id);


--
-- TOC entry 4545 (class 1259 OID 17811)
-- Name: ominicontacto_app_agenteensistemaexterno_agente_id_8a861404; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_agenteensistemaexterno_agente_id_8a861404 ON public.ominicontacto_app_agenteensistemaexterno USING btree (agente_id);


--
-- TOC entry 4272 (class 1259 OID 17130)
-- Name: ominicontacto_app_agenteprofile_grupo_id_474dfc5a; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_agenteprofile_grupo_id_474dfc5a ON public.ominicontacto_app_agenteprofile USING btree (grupo_id);


--
-- TOC entry 4275 (class 1259 OID 17150)
-- Name: ominicontacto_app_agenteprofile_reported_by_id_67c7fe30; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_agenteprofile_reported_by_id_67c7fe30 ON public.ominicontacto_app_agenteprofile USING btree (reported_by_id);


--
-- TOC entry 4280 (class 1259 OID 16910)
-- Name: ominicontacto_app_archivodeaudio_descripcion_e44e6cc0_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_archivodeaudio_descripcion_e44e6cc0_like ON public.ominicontacto_app_archivodeaudio USING btree (descripcion varchar_pattern_ops);


--
-- TOC entry 4592 (class 1259 OID 18150)
-- Name: ominicontacto_app_autent_nombre_5b3380fb_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_autent_nombre_5b3380fb_like ON public.ominicontacto_app_autenticacionsitioexterno USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4287 (class 1259 OID 17833)
-- Name: ominicontacto_app_basedatoscontacto_nombre_6cf964df_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_basedatoscontacto_nombre_6cf964df_like ON public.ominicontacto_app_basedatoscontacto USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4294 (class 1259 OID 17124)
-- Name: ominicontacto_app_califica_opcion_calificacion_id_5ad7e22c; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_califica_opcion_calificacion_id_5ad7e22c ON public.ominicontacto_app_calificacioncliente USING btree (opcion_calificacion_id);


--
-- TOC entry 4295 (class 1259 OID 16916)
-- Name: ominicontacto_app_calificacioncliente_agente_id_1070b434; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_calificacioncliente_agente_id_1070b434 ON public.ominicontacto_app_calificacioncliente USING btree (agente_id);


--
-- TOC entry 4296 (class 1259 OID 17118)
-- Name: ominicontacto_app_calificacioncliente_contacto_id_e5df4663; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_calificacioncliente_contacto_id_e5df4663 ON public.ominicontacto_app_calificacioncliente USING btree (contacto_id);


--
-- TOC entry 4299 (class 1259 OID 16923)
-- Name: ominicontacto_app_campana_bd_contacto_id_3b5858cd; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_campana_bd_contacto_id_3b5858cd ON public.ominicontacto_app_campana USING btree (bd_contacto_id);


--
-- TOC entry 4300 (class 1259 OID 16922)
-- Name: ominicontacto_app_campana_nombre_da9ee190_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_campana_nombre_da9ee190_like ON public.ominicontacto_app_campana USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4303 (class 1259 OID 17898)
-- Name: ominicontacto_app_campana_outr_id_2cd2dd43; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_campana_outr_id_2cd2dd43 ON public.ominicontacto_app_campana USING btree (outr_id);


--
-- TOC entry 4306 (class 1259 OID 17092)
-- Name: ominicontacto_app_campana_reported_by_id_cb70293d; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_campana_reported_by_id_cb70293d ON public.ominicontacto_app_campana USING btree (reported_by_id);


--
-- TOC entry 4307 (class 1259 OID 17816)
-- Name: ominicontacto_app_campana_sistema_externo_id_6654b990; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_campana_sistema_externo_id_6654b990 ON public.ominicontacto_app_campana USING btree (sistema_externo_id);


--
-- TOC entry 4308 (class 1259 OID 17098)
-- Name: ominicontacto_app_campana_sitio_externo_id_e255b47e; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_campana_sitio_externo_id_e255b47e ON public.ominicontacto_app_campana USING btree (sitio_externo_id);


--
-- TOC entry 4395 (class 1259 OID 17116)
-- Name: ominicontacto_app_campana_supervisors_campana_id_242d5c1e; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_campana_supervisors_campana_id_242d5c1e ON public.ominicontacto_app_campana_supervisors USING btree (campana_id);


--
-- TOC entry 4398 (class 1259 OID 17117)
-- Name: ominicontacto_app_campana_supervisors_user_id_7aafcfff; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_campana_supervisors_user_id_7aafcfff ON public.ominicontacto_app_campana_supervisors USING btree (user_id);


--
-- TOC entry 4309 (class 1259 OID 16934)
-- Name: ominicontacto_app_chat_agente_id_b0b74e82; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_chat_agente_id_b0b74e82 ON public.ominicontacto_app_chat USING btree (agente_id);


--
-- TOC entry 4312 (class 1259 OID 16935)
-- Name: ominicontacto_app_chat_user_id_7e593d05; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_chat_user_id_7e593d05 ON public.ominicontacto_app_chat USING btree (user_id);


--
-- TOC entry 4588 (class 1259 OID 18104)
-- Name: ominicontacto_app_configur_conjunto_de_pausa_id_87162770; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_configur_conjunto_de_pausa_id_87162770 ON public.ominicontacto_app_configuraciondepausa USING btree (conjunto_de_pausa_id);


--
-- TOC entry 4589 (class 1259 OID 18105)
-- Name: ominicontacto_app_configuraciondepausa_pausa_id_762e4a99; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_configuraciondepausa_pausa_id_762e4a99 ON public.ominicontacto_app_configuraciondepausa USING btree (pausa_id);


--
-- TOC entry 4313 (class 1259 OID 16941)
-- Name: ominicontacto_app_contacto_bd_contacto_id_e36d02df; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_contacto_bd_contacto_id_e36d02df ON public.ominicontacto_app_contacto USING btree (bd_contacto_id);


--
-- TOC entry 4558 (class 1259 OID 17955)
-- Name: ominicontacto_app_contactoblacklist_black_list_id_718e9765; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_contactoblacklist_black_list_id_718e9765 ON public.ominicontacto_app_contactoblacklist USING btree (black_list_id);


--
-- TOC entry 4561 (class 1259 OID 18067)
-- Name: ominicontacto_app_contactoblacklist_telefono_a1dfe877_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_contactoblacklist_telefono_a1dfe877_like ON public.ominicontacto_app_contactoblacklist USING btree (telefono varchar_pattern_ops);


--
-- TOC entry 4583 (class 1259 OID 18054)
-- Name: ominicontacto_app_contactolistarapida_lista_rapida_id_60bb61c9; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_contactolistarapida_lista_rapida_id_60bb61c9 ON public.ominicontacto_app_contactolistarapida USING btree (lista_rapida_id);


--
-- TOC entry 4318 (class 1259 OID 17080)
-- Name: ominicontacto_app_fieldformulario_formulario_id_b5355e5d; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_fieldformulario_formulario_id_b5355e5d ON public.ominicontacto_app_fieldformulario USING btree (formulario_id);


--
-- TOC entry 4325 (class 1259 OID 18106)
-- Name: ominicontacto_app_grupo_conjunto_de_pausa_id_8d3e5455; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_grupo_conjunto_de_pausa_id_8d3e5455 ON public.ominicontacto_app_grupo USING btree (conjunto_de_pausa_id);


--
-- TOC entry 4326 (class 1259 OID 17830)
-- Name: ominicontacto_app_grupo_nombre_09c6de5a_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_grupo_nombre_09c6de5a_like ON public.ominicontacto_app_grupo USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4333 (class 1259 OID 16972)
-- Name: ominicontacto_app_historic_agente_id_7d63ce43; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_historic_agente_id_7d63ce43 ON public.ominicontacto_app_historicalcalificacioncliente USING btree (agente_id);


--
-- TOC entry 4573 (class 1259 OID 18024)
-- Name: ominicontacto_app_historic_calificacion_id_24da2aa4; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_historic_calificacion_id_24da2aa4 ON public.ominicontacto_app_historicalrespuestaformulariogestion USING btree (calificacion_id);


--
-- TOC entry 4334 (class 1259 OID 16973)
-- Name: ominicontacto_app_historic_contacto_id_aead1f8a; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_historic_contacto_id_aead1f8a ON public.ominicontacto_app_historicalcalificacioncliente USING btree (contacto_id);


--
-- TOC entry 4574 (class 1259 OID 18025)
-- Name: ominicontacto_app_historic_history_user_id_2f174ef7; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_historic_history_user_id_2f174ef7 ON public.ominicontacto_app_historicalrespuestaformulariogestion USING btree (history_user_id);


--
-- TOC entry 4335 (class 1259 OID 16974)
-- Name: ominicontacto_app_historic_history_user_id_51068f0a; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_historic_history_user_id_51068f0a ON public.ominicontacto_app_historicalcalificacioncliente USING btree (history_user_id);


--
-- TOC entry 4575 (class 1259 OID 18023)
-- Name: ominicontacto_app_historic_id_52923dfd; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_historic_id_52923dfd ON public.ominicontacto_app_historicalrespuestaformulariogestion USING btree (id);


--
-- TOC entry 4336 (class 1259 OID 17079)
-- Name: ominicontacto_app_historic_opcion_calificacion_id_79ab054c; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_historic_opcion_calificacion_id_79ab054c ON public.ominicontacto_app_historicalcalificacioncliente USING btree (opcion_calificacion_id);


--
-- TOC entry 4337 (class 1259 OID 16971)
-- Name: ominicontacto_app_historicalcalificacioncliente_id_feb97abd; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_historicalcalificacioncliente_id_feb97abd ON public.ominicontacto_app_historicalcalificacioncliente USING btree (id);


--
-- TOC entry 4578 (class 1259 OID 18048)
-- Name: ominicontacto_app_listasrapidas_nombre_b70632ec_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_listasrapidas_nombre_b70632ec_like ON public.ominicontacto_app_listasrapidas USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4340 (class 1259 OID 16990)
-- Name: ominicontacto_app_mensajechat_chat_id_3845da5b; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_mensajechat_chat_id_3845da5b ON public.ominicontacto_app_mensajechat USING btree (chat_id);


--
-- TOC entry 4343 (class 1259 OID 16991)
-- Name: ominicontacto_app_mensajechat_sender_id_49a6c90d; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_mensajechat_sender_id_49a6c90d ON public.ominicontacto_app_mensajechat USING btree (sender_id);


--
-- TOC entry 4344 (class 1259 OID 16992)
-- Name: ominicontacto_app_mensajechat_to_id_a5f7aa2c; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_mensajechat_to_id_a5f7aa2c ON public.ominicontacto_app_mensajechat USING btree (to_id);


--
-- TOC entry 4350 (class 1259 OID 17022)
-- Name: ominicontacto_app_opcioncalificacion_campana_id_8feac367; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_opcioncalificacion_campana_id_8feac367 ON public.ominicontacto_app_opcioncalificacion USING btree (campana_id);


--
-- TOC entry 4351 (class 1259 OID 17528)
-- Name: ominicontacto_app_opcioncalificacion_formulario_id_a0906f50; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_opcioncalificacion_formulario_id_a0906f50 ON public.ominicontacto_app_opcioncalificacion USING btree (formulario_id);


--
-- TOC entry 4475 (class 1259 OID 17500)
-- Name: ominicontacto_app_parametroscrm_campana_id_c8dd4478; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_parametroscrm_campana_id_c8dd4478 ON public.ominicontacto_app_parametroscrm USING btree (campana_id);


--
-- TOC entry 4354 (class 1259 OID 17029)
-- Name: ominicontacto_app_pausa_nombre_0e58baeb_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_pausa_nombre_0e58baeb_like ON public.ominicontacto_app_pausa USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4378 (class 1259 OID 17072)
-- Name: ominicontacto_app_reglasincidencia_campana_id_707899e9; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_reglasincidencia_campana_id_707899e9 ON public.ominicontacto_app_reglasincidencia USING btree (campana_id);


--
-- TOC entry 4347 (class 1259 OID 17516)
-- Name: ominicontacto_app_respuest_calificacion_id_c0a65d38; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_respuest_calificacion_id_c0a65d38 ON public.ominicontacto_app_respuestaformulariogestion USING btree (calificacion_id);


--
-- TOC entry 4535 (class 1259 OID 17788)
-- Name: ominicontacto_app_sistemaexterno_nombre_6b0213f9_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_sistemaexterno_nombre_6b0213f9_like ON public.ominicontacto_app_sistemaexterno USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4381 (class 1259 OID 18151)
-- Name: ominicontacto_app_sitioexterno_autenticacion_id_659d1062; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_sitioexterno_autenticacion_id_659d1062 ON public.ominicontacto_app_sitioexterno USING btree (autenticacion_id);


--
-- TOC entry 4382 (class 1259 OID 18118)
-- Name: ominicontacto_app_sitioexterno_nombre_f6a98fa8_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_sitioexterno_nombre_f6a98fa8_like ON public.ominicontacto_app_sitioexterno USING btree (nombre varchar_pattern_ops);


--
-- TOC entry 4249 (class 1259 OID 16895)
-- Name: ominicontacto_app_user_groups_group_id_f47e61a0; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_user_groups_group_id_f47e61a0 ON public.ominicontacto_app_user_groups USING btree (group_id);


--
-- TOC entry 4252 (class 1259 OID 16894)
-- Name: ominicontacto_app_user_groups_user_id_9520c89f; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_user_groups_user_id_9520c89f ON public.ominicontacto_app_user_groups USING btree (user_id);


--
-- TOC entry 4257 (class 1259 OID 16909)
-- Name: ominicontacto_app_user_user_permissions_permission_id_43f9ab68; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_user_user_permissions_permission_id_43f9ab68 ON public.ominicontacto_app_user_user_permissions USING btree (permission_id);


--
-- TOC entry 4260 (class 1259 OID 16908)
-- Name: ominicontacto_app_user_user_permissions_user_id_4412e21b; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_user_user_permissions_user_id_4412e21b ON public.ominicontacto_app_user_user_permissions USING btree (user_id);


--
-- TOC entry 4246 (class 1259 OID 17861)
-- Name: ominicontacto_app_user_username_3223b7ba_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX ominicontacto_app_user_username_3223b7ba_like ON public.ominicontacto_app_user USING btree (username varchar_pattern_ops);


--
-- TOC entry 4371 (class 1259 OID 17064)
-- Name: queue_member_table_member_id_0e6c0aa5; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_member_table_member_id_0e6c0aa5 ON public.queue_member_table USING btree (member_id);


--
-- TOC entry 4374 (class 1259 OID 17065)
-- Name: queue_member_table_queue_name_cc6b888a; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_member_table_queue_name_cc6b888a ON public.queue_member_table USING btree (queue_name);


--
-- TOC entry 4375 (class 1259 OID 17066)
-- Name: queue_member_table_queue_name_cc6b888a_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_member_table_queue_name_cc6b888a_like ON public.queue_member_table USING btree (queue_name varchar_pattern_ops);


--
-- TOC entry 4359 (class 1259 OID 17051)
-- Name: queue_table_audio_de_ingreso_id_28e2a56e; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_table_audio_de_ingreso_id_28e2a56e ON public.queue_table USING btree (audio_de_ingreso_id);


--
-- TOC entry 4360 (class 1259 OID 17052)
-- Name: queue_table_audio_para_contestadores_id_49e13f02; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_table_audio_para_contestadores_id_49e13f02 ON public.queue_table USING btree (audio_para_contestadores_id);


--
-- TOC entry 4361 (class 1259 OID 17984)
-- Name: queue_table_audio_previo_conexion_llamada_id_5034bc70; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_table_audio_previo_conexion_llamada_id_5034bc70 ON public.queue_table USING btree (audio_previo_conexion_llamada_id);


--
-- TOC entry 4362 (class 1259 OID 17053)
-- Name: queue_table_audios_id_e9679a0c; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_table_audios_id_e9679a0c ON public.queue_table USING btree (audios_id);


--
-- TOC entry 4365 (class 1259 OID 17459)
-- Name: queue_table_destino_id_3b1b009f; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_table_destino_id_3b1b009f ON public.queue_table USING btree (destino_id);


--
-- TOC entry 4366 (class 1259 OID 17868)
-- Name: queue_table_ivr_breakdown_id_9d6d0bcd; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_table_ivr_breakdown_id_9d6d0bcd ON public.queue_table USING btree (ivr_breakdown_id);


--
-- TOC entry 4367 (class 1259 OID 17889)
-- Name: queue_table_musiconhold_id_207bcb8a; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_table_musiconhold_id_207bcb8a ON public.queue_table USING btree (musiconhold_id);


--
-- TOC entry 4368 (class 1259 OID 17050)
-- Name: queue_table_name_495baf91_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX queue_table_name_495baf91_like ON public.queue_table USING btree (name varchar_pattern_ops);


--
-- TOC entry 4597 (class 1259 OID 18181)
-- Name: reportes_app_actividadagentelog_agente_id_38e73968; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_actividadagentelog_agente_id_38e73968 ON public.reportes_app_actividadagentelog USING btree (agente_id);


--
-- TOC entry 4600 (class 1259 OID 18180)
-- Name: reportes_app_actividadagentelog_time_4a7497f0; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_actividadagentelog_time_4a7497f0 ON public.reportes_app_actividadagentelog USING btree ("time");


--
-- TOC entry 4601 (class 1259 OID 18185)
-- Name: reportes_app_llamadalog_agente_extra_id_ca22403c; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_llamadalog_agente_extra_id_ca22403c ON public.reportes_app_llamadalog USING btree (agente_extra_id);


--
-- TOC entry 4602 (class 1259 OID 18184)
-- Name: reportes_app_llamadalog_agente_id_3d1ab230; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_llamadalog_agente_id_3d1ab230 ON public.reportes_app_llamadalog USING btree (agente_id);


--
-- TOC entry 4603 (class 1259 OID 18211)
-- Name: reportes_app_llamadalog_callid_884693d3; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_llamadalog_callid_884693d3 ON public.reportes_app_llamadalog USING btree (callid);


--
-- TOC entry 4604 (class 1259 OID 18212)
-- Name: reportes_app_llamadalog_callid_884693d3_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_llamadalog_callid_884693d3_like ON public.reportes_app_llamadalog USING btree (callid varchar_pattern_ops);


--
-- TOC entry 4605 (class 1259 OID 18186)
-- Name: reportes_app_llamadalog_campana_extra_id_8bc4ec47; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_llamadalog_campana_extra_id_8bc4ec47 ON public.reportes_app_llamadalog USING btree (campana_extra_id);


--
-- TOC entry 4606 (class 1259 OID 18183)
-- Name: reportes_app_llamadalog_campana_id_7fb49db2; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_llamadalog_campana_id_7fb49db2 ON public.reportes_app_llamadalog USING btree (campana_id);


--
-- TOC entry 4607 (class 1259 OID 18213)
-- Name: reportes_app_llamadalog_contacto_id_fd04f51c; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_llamadalog_contacto_id_fd04f51c ON public.reportes_app_llamadalog USING btree (contacto_id);


--
-- TOC entry 4610 (class 1259 OID 18182)
-- Name: reportes_app_llamadalog_time_8669915f; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_llamadalog_time_8669915f ON public.reportes_app_llamadalog USING btree ("time");


--
-- TOC entry 4613 (class 1259 OID 18225)
-- Name: reportes_app_transferenciaaencuestalog_agente_id_aa506b5b; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_transferenciaaencuestalog_agente_id_aa506b5b ON public.reportes_app_transferenciaaencuestalog USING btree (agente_id);


--
-- TOC entry 4614 (class 1259 OID 18228)
-- Name: reportes_app_transferenciaaencuestalog_callid_08c60137; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_transferenciaaencuestalog_callid_08c60137 ON public.reportes_app_transferenciaaencuestalog USING btree (callid);


--
-- TOC entry 4615 (class 1259 OID 18229)
-- Name: reportes_app_transferenciaaencuestalog_callid_08c60137_like; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_transferenciaaencuestalog_callid_08c60137_like ON public.reportes_app_transferenciaaencuestalog USING btree (callid varchar_pattern_ops);


--
-- TOC entry 4616 (class 1259 OID 18226)
-- Name: reportes_app_transferenciaaencuestalog_campana_id_4e6ce747; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_transferenciaaencuestalog_campana_id_4e6ce747 ON public.reportes_app_transferenciaaencuestalog USING btree (campana_id);


--
-- TOC entry 4617 (class 1259 OID 18227)
-- Name: reportes_app_transferenciaaencuestalog_encuesta_id_d0946f96; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_transferenciaaencuestalog_encuesta_id_d0946f96 ON public.reportes_app_transferenciaaencuestalog USING btree (encuesta_id);


--
-- TOC entry 4620 (class 1259 OID 18224)
-- Name: reportes_app_transferenciaaencuestalog_time_dc477533; Type: INDEX; Schema: public; Owner: omnileads
--

CREATE INDEX reportes_app_transferenciaaencuestalog_time_dc477533 ON public.reportes_app_transferenciaaencuestalog USING btree ("time");


--
-- TOC entry 4707 (class 2620 OID 18215)
-- Name: queue_log trigger_queue_log; Type: TRIGGER; Schema: public; Owner: omnileads
--

CREATE TRIGGER trigger_queue_log AFTER INSERT ON public.queue_log FOR EACH ROW EXECUTE PROCEDURE public.insert_queue_log_ominicontacto_queue_log();


--
-- TOC entry 4630 (class 2606 OID 16452)
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4631 (class 2606 OID 16447)
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4629 (class 2606 OID 16438)
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4680 (class 2606 OID 17227)
-- Name: authtoken_token authtoken_token_user_id_35299eff_fk_ominicontacto_app_user_id; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_35299eff_fk_ominicontacto_app_user_id FOREIGN KEY (user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4694 (class 2606 OID 17557)
-- Name: configuracion_telefonia_app_identificadorcliente configuracion_telefo_audio_id_b57c0fee_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_identificadorcliente
    ADD CONSTRAINT configuracion_telefo_audio_id_b57c0fee_fk_ominicont FOREIGN KEY (audio_id) REFERENCES public.ominicontacto_app_archivodeaudio(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4682 (class 2606 OID 17379)
-- Name: configuracion_telefonia_app_ivr configuracion_telefo_audio_principal_id_f765af13_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ivr
    ADD CONSTRAINT configuracion_telefo_audio_principal_id_f765af13_fk_ominicont FOREIGN KEY (audio_principal_id) REFERENCES public.ominicontacto_app_archivodeaudio(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4681 (class 2606 OID 17371)
-- Name: configuracion_telefonia_app_destinoentrante configuracion_telefo_content_type_id_8f3d2b4d_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_destinoentrante
    ADD CONSTRAINT configuracion_telefo_content_type_id_8f3d2b4d_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4685 (class 2606 OID 17398)
-- Name: configuracion_telefonia_app_opciondestino configuracion_telefo_destino_anterior_id_0996ab3b_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_opciondestino
    ADD CONSTRAINT configuracion_telefo_destino_anterior_id_0996ab3b_fk_configura FOREIGN KEY (destino_anterior_id) REFERENCES public.configuracion_telefonia_app_destinoentrante(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4690 (class 2606 OID 17410)
-- Name: configuracion_telefonia_app_rutaentrante configuracion_telefo_destino_id_14fb9d9d_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_rutaentrante
    ADD CONSTRAINT configuracion_telefo_destino_id_14fb9d9d_fk_configura FOREIGN KEY (destino_id) REFERENCES public.configuracion_telefonia_app_destinoentrante(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4686 (class 2606 OID 17403)
-- Name: configuracion_telefonia_app_opciondestino configuracion_telefo_destino_siguiente_id_5baf22fc_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_opciondestino
    ADD CONSTRAINT configuracion_telefo_destino_siguiente_id_5baf22fc_fk_configura FOREIGN KEY (destino_siguiente_id) REFERENCES public.configuracion_telefonia_app_destinoentrante(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4691 (class 2606 OID 17534)
-- Name: configuracion_telefonia_app_validacionfechahora configuracion_telefo_grupo_horario_id_2a6d57f1_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_validacionfechahora
    ADD CONSTRAINT configuracion_telefo_grupo_horario_id_2a6d57f1_fk_configura FOREIGN KEY (grupo_horario_id) REFERENCES public.configuracion_telefonia_app_grupohorario(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4692 (class 2606 OID 17427)
-- Name: configuracion_telefonia_app_validaciontiempo configuracion_telefo_grupo_horario_id_d708e8ee_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_validaciontiempo
    ADD CONSTRAINT configuracion_telefo_grupo_horario_id_d708e8ee_fk_configura FOREIGN KEY (grupo_horario_id) REFERENCES public.configuracion_telefonia_app_grupohorario(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4683 (class 2606 OID 17384)
-- Name: configuracion_telefonia_app_ivr configuracion_telefo_invalid_audio_id_260b2a2a_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ivr
    ADD CONSTRAINT configuracion_telefo_invalid_audio_id_260b2a2a_fk_ominicont FOREIGN KEY (invalid_audio_id) REFERENCES public.ominicontacto_app_archivodeaudio(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4695 (class 2606 OID 17605)
-- Name: configuracion_telefonia_app_musicadeespera configuracion_telefo_playlist_id_9fb0431b_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_musicadeespera
    ADD CONSTRAINT configuracion_telefo_playlist_id_9fb0431b_fk_configura FOREIGN KEY (playlist_id) REFERENCES public.configuracion_telefonia_app_playlist(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4689 (class 2606 OID 17434)
-- Name: configuracion_telefonia_app_patrondediscado configuracion_telefo_ruta_saliente_id_7b111e0f_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_patrondediscado
    ADD CONSTRAINT configuracion_telefo_ruta_saliente_id_7b111e0f_fk_configura FOREIGN KEY (ruta_saliente_id) REFERENCES public.configuracion_telefonia_app_rutasaliente(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4687 (class 2606 OID 17440)
-- Name: configuracion_telefonia_app_ordentroncal configuracion_telefo_ruta_saliente_id_bd46bea8_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ordentroncal
    ADD CONSTRAINT configuracion_telefo_ruta_saliente_id_bd46bea8_fk_configura FOREIGN KEY (ruta_saliente_id) REFERENCES public.configuracion_telefonia_app_rutasaliente(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4684 (class 2606 OID 17389)
-- Name: configuracion_telefonia_app_ivr configuracion_telefo_time_out_audio_id_e2235eb3_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ivr
    ADD CONSTRAINT configuracion_telefo_time_out_audio_id_e2235eb3_fk_ominicont FOREIGN KEY (time_out_audio_id) REFERENCES public.ominicontacto_app_archivodeaudio(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4688 (class 2606 OID 17446)
-- Name: configuracion_telefonia_app_ordentroncal configuracion_telefo_troncal_id_edef8a14_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.configuracion_telefonia_app_ordentroncal
    ADD CONSTRAINT configuracion_telefo_troncal_id_edef8a14_fk_configura FOREIGN KEY (troncal_id) REFERENCES public.configuracion_telefonia_app_troncalsip(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4678 (class 2606 OID 17202)
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4679 (class 2606 OID 17207)
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_ominicontacto_app_user_id; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_ominicontacto_app_user_id FOREIGN KEY (user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4636 (class 2606 OID 17862)
-- Name: ominicontacto_app_actuacionvigente ominicontacto_app_ac_campana_id_24d4b93b_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_actuacionvigente
    ADD CONSTRAINT ominicontacto_app_ac_campana_id_24d4b93b_fk_ominicont FOREIGN KEY (campana_id) REFERENCES public.ominicontacto_app_campana(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4637 (class 2606 OID 17162)
-- Name: ominicontacto_app_agendacontacto ominicontacto_app_ag_agente_id_34ccaf4a_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agendacontacto
    ADD CONSTRAINT ominicontacto_app_ag_agente_id_34ccaf4a_fk_ominicont FOREIGN KEY (agente_id) REFERENCES public.ominicontacto_app_agenteprofile(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4696 (class 2606 OID 18125)
-- Name: ominicontacto_app_agenteensistemaexterno ominicontacto_app_ag_agente_id_8a861404_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteensistemaexterno
    ADD CONSTRAINT ominicontacto_app_ag_agente_id_8a861404_fk_ominicont FOREIGN KEY (agente_id) REFERENCES public.ominicontacto_app_agenteprofile(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4638 (class 2606 OID 17168)
-- Name: ominicontacto_app_agendacontacto ominicontacto_app_ag_campana_id_364b62ec_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agendacontacto
    ADD CONSTRAINT ominicontacto_app_ag_campana_id_364b62ec_fk_ominicont FOREIGN KEY (campana_id) REFERENCES public.ominicontacto_app_campana(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4639 (class 2606 OID 17174)
-- Name: ominicontacto_app_agendacontacto ominicontacto_app_ag_contacto_id_81a823de_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agendacontacto
    ADD CONSTRAINT ominicontacto_app_ag_contacto_id_81a823de_fk_ominicont FOREIGN KEY (contacto_id) REFERENCES public.ominicontacto_app_contacto(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4640 (class 2606 OID 17467)
-- Name: ominicontacto_app_agenteprofile ominicontacto_app_ag_grupo_id_474dfc5a_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteprofile
    ADD CONSTRAINT ominicontacto_app_ag_grupo_id_474dfc5a_fk_ominicont FOREIGN KEY (grupo_id) REFERENCES public.ominicontacto_app_grupo(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4641 (class 2606 OID 17151)
-- Name: ominicontacto_app_agenteprofile ominicontacto_app_ag_reported_by_id_67c7fe30_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteprofile
    ADD CONSTRAINT ominicontacto_app_ag_reported_by_id_67c7fe30_fk_ominicont FOREIGN KEY (reported_by_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4697 (class 2606 OID 18130)
-- Name: ominicontacto_app_agenteensistemaexterno ominicontacto_app_ag_sistema_externo_id_f6fba0d7_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteensistemaexterno
    ADD CONSTRAINT ominicontacto_app_ag_sistema_externo_id_f6fba0d7_fk_ominicont FOREIGN KEY (sistema_externo_id) REFERENCES public.ominicontacto_app_sistemaexterno(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4642 (class 2606 OID 17156)
-- Name: ominicontacto_app_agenteprofile ominicontacto_app_ag_user_id_0e446b03_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_agenteprofile
    ADD CONSTRAINT ominicontacto_app_ag_user_id_0e446b03_fk_ominicont FOREIGN KEY (user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4699 (class 2606 OID 17931)
-- Name: ominicontacto_app_auditoriacalificacion ominicontacto_app_au_calificacion_id_dd3d39f1_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_auditoriacalificacion
    ADD CONSTRAINT ominicontacto_app_au_calificacion_id_dd3d39f1_fk_ominicont FOREIGN KEY (calificacion_id) REFERENCES public.ominicontacto_app_calificacioncliente(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4643 (class 2606 OID 16911)
-- Name: ominicontacto_app_calificacioncliente ominicontacto_app_ca_agente_id_1070b434_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_calificacioncliente
    ADD CONSTRAINT ominicontacto_app_ca_agente_id_1070b434_fk_ominicont FOREIGN KEY (agente_id) REFERENCES public.ominicontacto_app_agenteprofile(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4646 (class 2606 OID 16917)
-- Name: ominicontacto_app_campana ominicontacto_app_ca_bd_contacto_id_3b5858cd_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana
    ADD CONSTRAINT ominicontacto_app_ca_bd_contacto_id_3b5858cd_fk_ominicont FOREIGN KEY (bd_contacto_id) REFERENCES public.ominicontacto_app_basedatoscontacto(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4676 (class 2606 OID 17104)
-- Name: ominicontacto_app_campana_supervisors ominicontacto_app_ca_campana_id_242d5c1e_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana_supervisors
    ADD CONSTRAINT ominicontacto_app_ca_campana_id_242d5c1e_fk_ominicont FOREIGN KEY (campana_id) REFERENCES public.ominicontacto_app_campana(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4644 (class 2606 OID 17119)
-- Name: ominicontacto_app_calificacioncliente ominicontacto_app_ca_contacto_id_e5df4663_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_calificacioncliente
    ADD CONSTRAINT ominicontacto_app_ca_contacto_id_e5df4663_fk_ominicont FOREIGN KEY (contacto_id) REFERENCES public.ominicontacto_app_contacto(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4645 (class 2606 OID 17125)
-- Name: ominicontacto_app_calificacioncliente ominicontacto_app_ca_opcion_calificacion__5ad7e22c_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_calificacioncliente
    ADD CONSTRAINT ominicontacto_app_ca_opcion_calificacion__5ad7e22c_fk_ominicont FOREIGN KEY (opcion_calificacion_id) REFERENCES public.ominicontacto_app_opcioncalificacion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4647 (class 2606 OID 17899)
-- Name: ominicontacto_app_campana ominicontacto_app_ca_outr_id_2cd2dd43_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana
    ADD CONSTRAINT ominicontacto_app_ca_outr_id_2cd2dd43_fk_configura FOREIGN KEY (outr_id) REFERENCES public.configuracion_telefonia_app_rutasaliente(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4648 (class 2606 OID 17093)
-- Name: ominicontacto_app_campana ominicontacto_app_ca_reported_by_id_cb70293d_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana
    ADD CONSTRAINT ominicontacto_app_ca_reported_by_id_cb70293d_fk_ominicont FOREIGN KEY (reported_by_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4649 (class 2606 OID 17817)
-- Name: ominicontacto_app_campana ominicontacto_app_ca_sistema_externo_id_6654b990_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana
    ADD CONSTRAINT ominicontacto_app_ca_sistema_externo_id_6654b990_fk_ominicont FOREIGN KEY (sistema_externo_id) REFERENCES public.ominicontacto_app_sistemaexterno(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4650 (class 2606 OID 17099)
-- Name: ominicontacto_app_campana ominicontacto_app_ca_sitio_externo_id_e255b47e_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana
    ADD CONSTRAINT ominicontacto_app_ca_sitio_externo_id_e255b47e_fk_ominicont FOREIGN KEY (sitio_externo_id) REFERENCES public.ominicontacto_app_sitioexterno(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4677 (class 2606 OID 17109)
-- Name: ominicontacto_app_campana_supervisors ominicontacto_app_ca_user_id_7aafcfff_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_campana_supervisors
    ADD CONSTRAINT ominicontacto_app_ca_user_id_7aafcfff_fk_ominicont FOREIGN KEY (user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4651 (class 2606 OID 16924)
-- Name: ominicontacto_app_chat ominicontacto_app_ch_agente_id_b0b74e82_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_chat
    ADD CONSTRAINT ominicontacto_app_ch_agente_id_b0b74e82_fk_ominicont FOREIGN KEY (agente_id) REFERENCES public.ominicontacto_app_agenteprofile(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4652 (class 2606 OID 16929)
-- Name: ominicontacto_app_chat ominicontacto_app_ch_user_id_7e593d05_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_chat
    ADD CONSTRAINT ominicontacto_app_ch_user_id_7e593d05_fk_ominicont FOREIGN KEY (user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4698 (class 2606 OID 17847)
-- Name: ominicontacto_app_clientewebphoneprofile ominicontacto_app_cl_user_id_bbe551e4_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_clientewebphoneprofile
    ADD CONSTRAINT ominicontacto_app_cl_user_id_bbe551e4_fk_ominicont FOREIGN KEY (user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4653 (class 2606 OID 16936)
-- Name: ominicontacto_app_contacto ominicontacto_app_co_bd_contacto_id_e36d02df_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contacto
    ADD CONSTRAINT ominicontacto_app_co_bd_contacto_id_e36d02df_fk_ominicont FOREIGN KEY (bd_contacto_id) REFERENCES public.ominicontacto_app_basedatoscontacto(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4700 (class 2606 OID 17956)
-- Name: ominicontacto_app_contactoblacklist ominicontacto_app_co_black_list_id_718e9765_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contactoblacklist
    ADD CONSTRAINT ominicontacto_app_co_black_list_id_718e9765_fk_ominicont FOREIGN KEY (black_list_id) REFERENCES public.ominicontacto_app_blacklist(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4702 (class 2606 OID 18001)
-- Name: ominicontacto_app_configuraciondeagentesdecampana ominicontacto_app_co_campana_id_cf9a53c6_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_configuraciondeagentesdecampana
    ADD CONSTRAINT ominicontacto_app_co_campana_id_cf9a53c6_fk_ominicont FOREIGN KEY (campana_id) REFERENCES public.ominicontacto_app_campana(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4705 (class 2606 OID 18094)
-- Name: ominicontacto_app_configuraciondepausa ominicontacto_app_co_conjunto_de_pausa_id_87162770_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_configuraciondepausa
    ADD CONSTRAINT ominicontacto_app_co_conjunto_de_pausa_id_87162770_fk_ominicont FOREIGN KEY (conjunto_de_pausa_id) REFERENCES public.ominicontacto_app_conjuntodepausa(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4704 (class 2606 OID 18049)
-- Name: ominicontacto_app_contactolistarapida ominicontacto_app_co_lista_rapida_id_60bb61c9_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_contactolistarapida
    ADD CONSTRAINT ominicontacto_app_co_lista_rapida_id_60bb61c9_fk_ominicont FOREIGN KEY (lista_rapida_id) REFERENCES public.ominicontacto_app_listasrapidas(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4706 (class 2606 OID 18099)
-- Name: ominicontacto_app_configuraciondepausa ominicontacto_app_co_pausa_id_762e4a99_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_configuraciondepausa
    ADD CONSTRAINT ominicontacto_app_co_pausa_id_762e4a99_fk_ominicont FOREIGN KEY (pausa_id) REFERENCES public.ominicontacto_app_pausa(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4654 (class 2606 OID 17081)
-- Name: ominicontacto_app_fieldformulario ominicontacto_app_fi_formulario_id_b5355e5d_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_fieldformulario
    ADD CONSTRAINT ominicontacto_app_fi_formulario_id_b5355e5d_fk_ominicont FOREIGN KEY (formulario_id) REFERENCES public.ominicontacto_app_formulario(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4655 (class 2606 OID 18107)
-- Name: ominicontacto_app_grupo ominicontacto_app_gr_conjunto_de_pausa_id_8d3e5455_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_grupo
    ADD CONSTRAINT ominicontacto_app_gr_conjunto_de_pausa_id_8d3e5455_fk_ominicont FOREIGN KEY (conjunto_de_pausa_id) REFERENCES public.ominicontacto_app_conjuntodepausa(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4703 (class 2606 OID 18018)
-- Name: ominicontacto_app_historicalrespuestaformulariogestion ominicontacto_app_hi_history_user_id_2f174ef7_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_historicalrespuestaformulariogestion
    ADD CONSTRAINT ominicontacto_app_hi_history_user_id_2f174ef7_fk_ominicont FOREIGN KEY (history_user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4656 (class 2606 OID 16966)
-- Name: ominicontacto_app_historicalcalificacioncliente ominicontacto_app_hi_history_user_id_51068f0a_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_historicalcalificacioncliente
    ADD CONSTRAINT ominicontacto_app_hi_history_user_id_51068f0a_fk_ominicont FOREIGN KEY (history_user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4657 (class 2606 OID 16975)
-- Name: ominicontacto_app_mensajechat ominicontacto_app_me_chat_id_3845da5b_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_mensajechat
    ADD CONSTRAINT ominicontacto_app_me_chat_id_3845da5b_fk_ominicont FOREIGN KEY (chat_id) REFERENCES public.ominicontacto_app_chat(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4658 (class 2606 OID 16980)
-- Name: ominicontacto_app_mensajechat ominicontacto_app_me_sender_id_49a6c90d_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_mensajechat
    ADD CONSTRAINT ominicontacto_app_me_sender_id_49a6c90d_fk_ominicont FOREIGN KEY (sender_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4659 (class 2606 OID 16985)
-- Name: ominicontacto_app_mensajechat ominicontacto_app_me_to_id_a5f7aa2c_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_mensajechat
    ADD CONSTRAINT ominicontacto_app_me_to_id_a5f7aa2c_fk_ominicont FOREIGN KEY (to_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4661 (class 2606 OID 17017)
-- Name: ominicontacto_app_opcioncalificacion ominicontacto_app_op_campana_id_8feac367_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_opcioncalificacion
    ADD CONSTRAINT ominicontacto_app_op_campana_id_8feac367_fk_ominicont FOREIGN KEY (campana_id) REFERENCES public.ominicontacto_app_campana(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4662 (class 2606 OID 17529)
-- Name: ominicontacto_app_opcioncalificacion ominicontacto_app_op_formulario_id_a0906f50_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_opcioncalificacion
    ADD CONSTRAINT ominicontacto_app_op_formulario_id_a0906f50_fk_ominicont FOREIGN KEY (formulario_id) REFERENCES public.ominicontacto_app_formulario(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4693 (class 2606 OID 17495)
-- Name: ominicontacto_app_parametroscrm ominicontacto_app_pa_campana_id_c8dd4478_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_parametroscrm
    ADD CONSTRAINT ominicontacto_app_pa_campana_id_c8dd4478_fk_ominicont FOREIGN KEY (campana_id) REFERENCES public.ominicontacto_app_campana(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4660 (class 2606 OID 17523)
-- Name: ominicontacto_app_respuestaformulariogestion ominicontacto_app_re_calificacion_id_c0a65d38_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_respuestaformulariogestion
    ADD CONSTRAINT ominicontacto_app_re_calificacion_id_c0a65d38_fk_ominicont FOREIGN KEY (calificacion_id) REFERENCES public.ominicontacto_app_calificacioncliente(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4673 (class 2606 OID 17067)
-- Name: ominicontacto_app_reglasincidencia ominicontacto_app_re_campana_id_707899e9_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_reglasincidencia
    ADD CONSTRAINT ominicontacto_app_re_campana_id_707899e9_fk_ominicont FOREIGN KEY (campana_id) REFERENCES public.ominicontacto_app_campana(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4701 (class 2606 OID 17979)
-- Name: ominicontacto_app_reglaincidenciaporcalificacion ominicontacto_app_re_opcion_calificacion__ac76a6d5_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_reglaincidenciaporcalificacion
    ADD CONSTRAINT ominicontacto_app_re_opcion_calificacion__ac76a6d5_fk_ominicont FOREIGN KEY (opcion_calificacion_id) REFERENCES public.ominicontacto_app_opcioncalificacion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4674 (class 2606 OID 18152)
-- Name: ominicontacto_app_sitioexterno ominicontacto_app_si_autenticacion_id_659d1062_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_sitioexterno
    ADD CONSTRAINT ominicontacto_app_si_autenticacion_id_659d1062_fk_ominicont FOREIGN KEY (autenticacion_id) REFERENCES public.ominicontacto_app_autenticacionsitioexterno(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4675 (class 2606 OID 17073)
-- Name: ominicontacto_app_supervisorprofile ominicontacto_app_su_user_id_e8fa6d81_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_supervisorprofile
    ADD CONSTRAINT ominicontacto_app_su_user_id_e8fa6d81_fk_ominicont FOREIGN KEY (user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4632 (class 2606 OID 16887)
-- Name: ominicontacto_app_user_groups ominicontacto_app_us_group_id_f47e61a0_fk_auth_grou; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_groups
    ADD CONSTRAINT ominicontacto_app_us_group_id_f47e61a0_fk_auth_grou FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4634 (class 2606 OID 16901)
-- Name: ominicontacto_app_user_user_permissions ominicontacto_app_us_permission_id_43f9ab68_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_user_permissions
    ADD CONSTRAINT ominicontacto_app_us_permission_id_43f9ab68_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4635 (class 2606 OID 16896)
-- Name: ominicontacto_app_user_user_permissions ominicontacto_app_us_user_id_4412e21b_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_user_permissions
    ADD CONSTRAINT ominicontacto_app_us_user_id_4412e21b_fk_ominicont FOREIGN KEY (user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4633 (class 2606 OID 16882)
-- Name: ominicontacto_app_user_groups ominicontacto_app_us_user_id_9520c89f_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.ominicontacto_app_user_groups
    ADD CONSTRAINT ominicontacto_app_us_user_id_9520c89f_fk_ominicont FOREIGN KEY (user_id) REFERENCES public.ominicontacto_app_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4671 (class 2606 OID 17054)
-- Name: queue_member_table queue_member_table_member_id_0e6c0aa5_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_member_table
    ADD CONSTRAINT queue_member_table_member_id_0e6c0aa5_fk_ominicont FOREIGN KEY (member_id) REFERENCES public.ominicontacto_app_agenteprofile(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4672 (class 2606 OID 17059)
-- Name: queue_member_table queue_member_table_queue_name_cc6b888a_fk_queue_table_name; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_member_table
    ADD CONSTRAINT queue_member_table_queue_name_cc6b888a_fk_queue_table_name FOREIGN KEY (queue_name) REFERENCES public.queue_table(name) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4663 (class 2606 OID 17030)
-- Name: queue_table queue_table_audio_de_ingreso_id_28e2a56e_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_audio_de_ingreso_id_28e2a56e_fk_ominicont FOREIGN KEY (audio_de_ingreso_id) REFERENCES public.ominicontacto_app_archivodeaudio(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4664 (class 2606 OID 17035)
-- Name: queue_table queue_table_audio_para_contestad_49e13f02_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_audio_para_contestad_49e13f02_fk_ominicont FOREIGN KEY (audio_para_contestadores_id) REFERENCES public.ominicontacto_app_archivodeaudio(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4665 (class 2606 OID 17985)
-- Name: queue_table queue_table_audio_previo_conexio_5034bc70_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_audio_previo_conexio_5034bc70_fk_ominicont FOREIGN KEY (audio_previo_conexion_llamada_id) REFERENCES public.ominicontacto_app_archivodeaudio(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4666 (class 2606 OID 17040)
-- Name: queue_table queue_table_audios_id_e9679a0c_fk_ominicont; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_audios_id_e9679a0c_fk_ominicont FOREIGN KEY (audios_id) REFERENCES public.ominicontacto_app_archivodeaudio(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4667 (class 2606 OID 17045)
-- Name: queue_table queue_table_campana_id_be72b1c4_fk_ominicontacto_app_campana_id; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_campana_id_be72b1c4_fk_ominicontacto_app_campana_id FOREIGN KEY (campana_id) REFERENCES public.ominicontacto_app_campana(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4668 (class 2606 OID 17460)
-- Name: queue_table queue_table_destino_id_3b1b009f_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_destino_id_3b1b009f_fk_configura FOREIGN KEY (destino_id) REFERENCES public.configuracion_telefonia_app_destinoentrante(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4669 (class 2606 OID 18158)
-- Name: queue_table queue_table_ivr_breakdown_id_9d6d0bcd_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_ivr_breakdown_id_9d6d0bcd_fk_configura FOREIGN KEY (ivr_breakdown_id) REFERENCES public.configuracion_telefonia_app_destinoentrante(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4670 (class 2606 OID 17890)
-- Name: queue_table queue_table_musiconhold_id_207bcb8a_fk_configura; Type: FK CONSTRAINT; Schema: public; Owner: omnileads
--

ALTER TABLE ONLY public.queue_table
    ADD CONSTRAINT queue_table_musiconhold_id_207bcb8a_fk_configura FOREIGN KEY (musiconhold_id) REFERENCES public.configuracion_telefonia_app_playlist(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4834 (class 0 OID 0)
-- Dependencies: 7
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- TOC entry 4836 (class 0 OID 0)
-- Dependencies: 204
-- Name: TABLE auth_group; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.auth_group TO efivoz;


--
-- TOC entry 4838 (class 0 OID 0)
-- Dependencies: 206
-- Name: TABLE auth_group_permissions; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.auth_group_permissions TO efivoz;


--
-- TOC entry 4840 (class 0 OID 0)
-- Dependencies: 202
-- Name: TABLE auth_permission; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.auth_permission TO efivoz;


--
-- TOC entry 4842 (class 0 OID 0)
-- Dependencies: 268
-- Name: TABLE authtoken_token; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.authtoken_token TO efivoz;


--
-- TOC entry 4843 (class 0 OID 0)
-- Dependencies: 304
-- Name: TABLE configuracion_telefonia_app_amdconf; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_amdconf TO efivoz;


--
-- TOC entry 4845 (class 0 OID 0)
-- Dependencies: 308
-- Name: TABLE configuracion_telefonia_app_audiosasteriskconf; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_audiosasteriskconf TO efivoz;


--
-- TOC entry 4847 (class 0 OID 0)
-- Dependencies: 270
-- Name: TABLE configuracion_telefonia_app_destinoentrante; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_destinoentrante TO efivoz;


--
-- TOC entry 4849 (class 0 OID 0)
-- Dependencies: 298
-- Name: TABLE configuracion_telefonia_app_destinopersonalizado; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_destinopersonalizado TO efivoz;


--
-- TOC entry 4851 (class 0 OID 0)
-- Dependencies: 306
-- Name: TABLE configuracion_telefonia_app_esquemagrabaciones; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_esquemagrabaciones TO efivoz;


--
-- TOC entry 4853 (class 0 OID 0)
-- Dependencies: 272
-- Name: TABLE configuracion_telefonia_app_grupohorario; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_grupohorario TO efivoz;


--
-- TOC entry 4855 (class 0 OID 0)
-- Dependencies: 292
-- Name: TABLE configuracion_telefonia_app_hangup; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_hangup TO efivoz;


--
-- TOC entry 4857 (class 0 OID 0)
-- Dependencies: 296
-- Name: TABLE configuracion_telefonia_app_identificadorcliente; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_identificadorcliente TO efivoz;


--
-- TOC entry 4859 (class 0 OID 0)
-- Dependencies: 274
-- Name: TABLE configuracion_telefonia_app_ivr; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_ivr TO efivoz;


--
-- TOC entry 4861 (class 0 OID 0)
-- Dependencies: 300
-- Name: TABLE configuracion_telefonia_app_musicadeespera; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_musicadeespera TO efivoz;


--
-- TOC entry 4863 (class 0 OID 0)
-- Dependencies: 276
-- Name: TABLE configuracion_telefonia_app_opciondestino; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_opciondestino TO efivoz;


--
-- TOC entry 4865 (class 0 OID 0)
-- Dependencies: 278
-- Name: TABLE configuracion_telefonia_app_ordentroncal; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_ordentroncal TO efivoz;


--
-- TOC entry 4867 (class 0 OID 0)
-- Dependencies: 280
-- Name: TABLE configuracion_telefonia_app_patrondediscado; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_patrondediscado TO efivoz;


--
-- TOC entry 4869 (class 0 OID 0)
-- Dependencies: 302
-- Name: TABLE configuracion_telefonia_app_playlist; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_playlist TO efivoz;


--
-- TOC entry 4871 (class 0 OID 0)
-- Dependencies: 282
-- Name: TABLE configuracion_telefonia_app_rutaentrante; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_rutaentrante TO efivoz;


--
-- TOC entry 4873 (class 0 OID 0)
-- Dependencies: 284
-- Name: TABLE configuracion_telefonia_app_rutasaliente; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_rutasaliente TO efivoz;


--
-- TOC entry 4875 (class 0 OID 0)
-- Dependencies: 286
-- Name: TABLE configuracion_telefonia_app_troncalsip; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_troncalsip TO efivoz;


--
-- TOC entry 4877 (class 0 OID 0)
-- Dependencies: 288
-- Name: TABLE configuracion_telefonia_app_validacionfechahora; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_validacionfechahora TO efivoz;


--
-- TOC entry 4879 (class 0 OID 0)
-- Dependencies: 290
-- Name: TABLE configuracion_telefonia_app_validaciontiempo; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.configuracion_telefonia_app_validaciontiempo TO efivoz;


--
-- TOC entry 4881 (class 0 OID 0)
-- Dependencies: 310
-- Name: TABLE constance_config; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.constance_config TO efivoz;


--
-- TOC entry 4883 (class 0 OID 0)
-- Dependencies: 312
-- Name: TABLE defender_accessattempt; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.defender_accessattempt TO efivoz;


--
-- TOC entry 4885 (class 0 OID 0)
-- Dependencies: 267
-- Name: TABLE django_admin_log; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.django_admin_log TO efivoz;


--
-- TOC entry 4887 (class 0 OID 0)
-- Dependencies: 200
-- Name: TABLE django_content_type; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.django_content_type TO efivoz;


--
-- TOC entry 4889 (class 0 OID 0)
-- Dependencies: 198
-- Name: TABLE django_migrations; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.django_migrations TO efivoz;


--
-- TOC entry 4891 (class 0 OID 0)
-- Dependencies: 353
-- Name: TABLE django_session; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.django_session TO efivoz;


--
-- TOC entry 4892 (class 0 OID 0)
-- Dependencies: 314
-- Name: TABLE easyaudit_crudevent; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.easyaudit_crudevent TO efivoz;


--
-- TOC entry 4894 (class 0 OID 0)
-- Dependencies: 316
-- Name: TABLE easyaudit_loginevent; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.easyaudit_loginevent TO efivoz;


--
-- TOC entry 4896 (class 0 OID 0)
-- Dependencies: 318
-- Name: TABLE easyaudit_requestevent; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.easyaudit_requestevent TO efivoz;


--
-- TOC entry 4898 (class 0 OID 0)
-- Dependencies: 355
-- Name: TABLE form_app_encuesta; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.form_app_encuesta TO efivoz;


--
-- TOC entry 4900 (class 0 OID 0)
-- Dependencies: 357
-- Name: TABLE form_app_formulario; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.form_app_formulario TO efivoz;


--
-- TOC entry 4902 (class 0 OID 0)
-- Dependencies: 214
-- Name: TABLE ominicontacto_app_actuacionvigente; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_actuacionvigente TO efivoz;


--
-- TOC entry 4904 (class 0 OID 0)
-- Dependencies: 216
-- Name: TABLE ominicontacto_app_agendacontacto; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_agendacontacto TO efivoz;


--
-- TOC entry 4906 (class 0 OID 0)
-- Dependencies: 218
-- Name: TABLE ominicontacto_app_agenteencontacto; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_agenteencontacto TO efivoz;


--
-- TOC entry 4908 (class 0 OID 0)
-- Dependencies: 322
-- Name: TABLE ominicontacto_app_agenteensistemaexterno; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_agenteensistemaexterno TO efivoz;


--
-- TOC entry 4910 (class 0 OID 0)
-- Dependencies: 220
-- Name: TABLE ominicontacto_app_agenteprofile; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_agenteprofile TO efivoz;


--
-- TOC entry 4912 (class 0 OID 0)
-- Dependencies: 222
-- Name: TABLE ominicontacto_app_archivodeaudio; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_archivodeaudio TO efivoz;


--
-- TOC entry 4914 (class 0 OID 0)
-- Dependencies: 326
-- Name: TABLE ominicontacto_app_auditoriacalificacion; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_auditoriacalificacion TO efivoz;


--
-- TOC entry 4916 (class 0 OID 0)
-- Dependencies: 344
-- Name: TABLE ominicontacto_app_autenticacionsitioexterno; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_autenticacionsitioexterno TO efivoz;


--
-- TOC entry 4918 (class 0 OID 0)
-- Dependencies: 224
-- Name: TABLE ominicontacto_app_blacklist; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_blacklist TO efivoz;


--
-- TOC entry 4920 (class 0 OID 0)
-- Dependencies: 226
-- Name: TABLE ominicontacto_app_basedatoscontacto; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_basedatoscontacto TO efivoz;


--
-- TOC entry 4922 (class 0 OID 0)
-- Dependencies: 228
-- Name: TABLE ominicontacto_app_calificacioncliente; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_calificacioncliente TO efivoz;


--
-- TOC entry 4924 (class 0 OID 0)
-- Dependencies: 230
-- Name: TABLE ominicontacto_app_campana; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_campana TO efivoz;


--
-- TOC entry 4926 (class 0 OID 0)
-- Dependencies: 265
-- Name: TABLE ominicontacto_app_campana_supervisors; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_campana_supervisors TO efivoz;


--
-- TOC entry 4928 (class 0 OID 0)
-- Dependencies: 232
-- Name: TABLE ominicontacto_app_chat; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_chat TO efivoz;


--
-- TOC entry 4930 (class 0 OID 0)
-- Dependencies: 324
-- Name: TABLE ominicontacto_app_clientewebphoneprofile; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_clientewebphoneprofile TO efivoz;


--
-- TOC entry 4932 (class 0 OID 0)
-- Dependencies: 332
-- Name: TABLE ominicontacto_app_configuraciondeagentesdecampana; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_configuraciondeagentesdecampana TO efivoz;


--
-- TOC entry 4934 (class 0 OID 0)
-- Dependencies: 342
-- Name: TABLE ominicontacto_app_configuraciondepausa; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_configuraciondepausa TO efivoz;


--
-- TOC entry 4936 (class 0 OID 0)
-- Dependencies: 340
-- Name: TABLE ominicontacto_app_conjuntodepausa; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_conjuntodepausa TO efivoz;


--
-- TOC entry 4938 (class 0 OID 0)
-- Dependencies: 234
-- Name: TABLE ominicontacto_app_contacto; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_contacto TO efivoz;


--
-- TOC entry 4940 (class 0 OID 0)
-- Dependencies: 328
-- Name: TABLE ominicontacto_app_contactoblacklist; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_contactoblacklist TO efivoz;


--
-- TOC entry 4942 (class 0 OID 0)
-- Dependencies: 338
-- Name: TABLE ominicontacto_app_contactolistarapida; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_contactolistarapida TO efivoz;


--
-- TOC entry 4944 (class 0 OID 0)
-- Dependencies: 236
-- Name: TABLE ominicontacto_app_fieldformulario; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_fieldformulario TO efivoz;


--
-- TOC entry 4946 (class 0 OID 0)
-- Dependencies: 238
-- Name: TABLE ominicontacto_app_formulario; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_formulario TO efivoz;


--
-- TOC entry 4948 (class 0 OID 0)
-- Dependencies: 240
-- Name: TABLE ominicontacto_app_grabacion_marca; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_grabacion_marca TO efivoz;


--
-- TOC entry 4950 (class 0 OID 0)
-- Dependencies: 242
-- Name: TABLE ominicontacto_app_grupo; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_grupo TO efivoz;


--
-- TOC entry 4952 (class 0 OID 0)
-- Dependencies: 244
-- Name: TABLE ominicontacto_app_historicalcalificacioncliente; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_historicalcalificacioncliente TO efivoz;


--
-- TOC entry 4954 (class 0 OID 0)
-- Dependencies: 334
-- Name: TABLE ominicontacto_app_historicalrespuestaformulariogestion; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_historicalrespuestaformulariogestion TO efivoz;


--
-- TOC entry 4956 (class 0 OID 0)
-- Dependencies: 336
-- Name: TABLE ominicontacto_app_listasrapidas; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_listasrapidas TO efivoz;


--
-- TOC entry 4958 (class 0 OID 0)
-- Dependencies: 246
-- Name: TABLE ominicontacto_app_mensajechat; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_mensajechat TO efivoz;


--
-- TOC entry 4960 (class 0 OID 0)
-- Dependencies: 248
-- Name: TABLE ominicontacto_app_respuestaformulariogestion; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_respuestaformulariogestion TO efivoz;


--
-- TOC entry 4962 (class 0 OID 0)
-- Dependencies: 250
-- Name: TABLE ominicontacto_app_nombrecalificacion; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_nombrecalificacion TO efivoz;


--
-- TOC entry 4964 (class 0 OID 0)
-- Dependencies: 252
-- Name: TABLE ominicontacto_app_opcioncalificacion; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_opcioncalificacion TO efivoz;


--
-- TOC entry 4966 (class 0 OID 0)
-- Dependencies: 294
-- Name: TABLE ominicontacto_app_parametroscrm; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_parametroscrm TO efivoz;


--
-- TOC entry 4968 (class 0 OID 0)
-- Dependencies: 254
-- Name: TABLE ominicontacto_app_pausa; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_pausa TO efivoz;


--
-- TOC entry 4970 (class 0 OID 0)
-- Dependencies: 330
-- Name: TABLE ominicontacto_app_reglaincidenciaporcalificacion; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_reglaincidenciaporcalificacion TO efivoz;


--
-- TOC entry 4972 (class 0 OID 0)
-- Dependencies: 259
-- Name: TABLE ominicontacto_app_reglasincidencia; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_reglasincidencia TO efivoz;


--
-- TOC entry 4974 (class 0 OID 0)
-- Dependencies: 320
-- Name: TABLE ominicontacto_app_sistemaexterno; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_sistemaexterno TO efivoz;


--
-- TOC entry 4976 (class 0 OID 0)
-- Dependencies: 261
-- Name: TABLE ominicontacto_app_sitioexterno; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_sitioexterno TO efivoz;


--
-- TOC entry 4978 (class 0 OID 0)
-- Dependencies: 263
-- Name: TABLE ominicontacto_app_supervisorprofile; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_supervisorprofile TO efivoz;


--
-- TOC entry 4980 (class 0 OID 0)
-- Dependencies: 208
-- Name: TABLE ominicontacto_app_user; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_user TO efivoz;


--
-- TOC entry 4981 (class 0 OID 0)
-- Dependencies: 210
-- Name: TABLE ominicontacto_app_user_groups; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_user_groups TO efivoz;


--
-- TOC entry 4984 (class 0 OID 0)
-- Dependencies: 212
-- Name: TABLE ominicontacto_app_user_user_permissions; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.ominicontacto_app_user_user_permissions TO efivoz;


--
-- TOC entry 4986 (class 0 OID 0)
-- Dependencies: 350
-- Name: TABLE queue_log; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.queue_log TO efivoz;


--
-- TOC entry 4988 (class 0 OID 0)
-- Dependencies: 257
-- Name: TABLE queue_member_table; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.queue_member_table TO efivoz;


--
-- TOC entry 4990 (class 0 OID 0)
-- Dependencies: 255
-- Name: TABLE queue_table; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.queue_table TO efivoz;


--
-- TOC entry 4991 (class 0 OID 0)
-- Dependencies: 346
-- Name: TABLE reportes_app_actividadagentelog; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.reportes_app_actividadagentelog TO efivoz;


--
-- TOC entry 4993 (class 0 OID 0)
-- Dependencies: 348
-- Name: TABLE reportes_app_llamadalog; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.reportes_app_llamadalog TO efivoz;


--
-- TOC entry 4995 (class 0 OID 0)
-- Dependencies: 352
-- Name: TABLE reportes_app_transferenciaaencuestalog; Type: ACL; Schema: public; Owner: omnileads
--

GRANT SELECT ON TABLE public.reportes_app_transferenciaaencuestalog TO efivoz;


-- Completed on 2025-10-22 15:14:03

--
-- PostgreSQL database dump complete
--

