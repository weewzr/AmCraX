//! CoolProp 8.0.0 back end of the AmCraX fluid properties ([`amcrax_engine::props::FluidProps`]).
//!
//! CoolProp (<http://www.coolprop.org>, MIT License; licence text: [`licence`]) is built from
//! its C++ sources at the pinned commit `ae81610e7d23efc57f9d051c8e70a4d66e87537f` (tag
//! v8.0.0, the commit of the Python wheel `CoolProp.__gitrevision__` that produced the golden
//! tables) as a static library **in CI only** and linked when `COOLPROP_LIB_DIR` is set at
//! build time. Without it this crate builds in stub mode: there is no FFI and
//! [`CoolPropBackend::new`] fails.
//!
//! The FFI is the documented C interface of CoolProp (`include/CoolPropLib.h`): `PropsSI`,
//! `Props1SI`, `get_global_param_string`, `get_param_index`, `get_input_pair_index` and the
//! `AbstractState_*` handle functions. `unsafe` code is confined to the private `ffi` module of
//! this crate (every other crate of the workspace forbids it); each call passes NUL-terminated
//! strings that outlive the call, an error-code pointer and a message buffer with its true
//! length, and a handle returned by `AbstractState_factory`. All calls are serialised by one
//! mutex (CoolProp's global caches are not documented as thread-safe).
//!
//! The calls mirror the Python reference exactly: phase `none` uses `PropsSI` (CoolProp's own
//! phase determination), imposed liquid / gas use one reused `AbstractState("HEOS", fluid)` per
//! imposed phase with `specify_phase` and `update(PT_INPUTS, P, T)`, as
//! `process_model/properties.py` does; saturation calls use `PropsSI` with `Q` inputs. The
//! reference state is CoolProp's default for each fluid (never changed, as in Python).

use amcrax_engine::EngineError;
use amcrax_engine::props::{FluidProps, Query};

/// The CoolProp licence text embedded at build time (or a note that CoolProp is not linked).
pub fn licence() -> &'static str {
    include_str!(concat!(env!("OUT_DIR"), "/coolprop_licence.txt"))
}

/// Whether CoolProp is linked into this build.
pub fn linked() -> bool {
    cfg!(coolprop_linked)
}

/// CoolProp back end.
pub struct CoolPropBackend {
    #[cfg(coolprop_linked)]
    inner: std::sync::Mutex<ffi::State>,
}

impl CoolPropBackend {
    /// Open the back end (fails in stub mode or when CoolProp cannot create its states).
    pub fn new() -> Result<CoolPropBackend, EngineError> {
        #[cfg(coolprop_linked)]
        {
            Ok(CoolPropBackend {
                inner: std::sync::Mutex::new(ffi::State::new()?),
            })
        }
        #[cfg(not(coolprop_linked))]
        {
            Err(EngineError::Property(
                "CoolProp is not linked into this build (build amcrax-cli with --features coolprop and \
                 COOLPROP_LIB_DIR pointing to the CoolProp static library, as the CI job `coolprop` does)"
                    .into(),
            ))
        }
    }

    /// CoolProp's version and git revision (`get_global_param_string`).
    pub fn version(&self) -> String {
        #[cfg(coolprop_linked)]
        {
            format!(
                "{} ({})",
                ffi::global_string("version"),
                ffi::global_string("gitrevision")
            )
        }
        #[cfg(not(coolprop_linked))]
        {
            "not linked".into()
        }
    }
}

impl FluidProps for CoolPropBackend {
    fn backend(&self) -> &'static str {
        "coolprop"
    }

    #[cfg(coolprop_linked)]
    fn value(&self, q: &Query) -> Result<f64, EngineError> {
        let mut st = self
            .inner
            .lock()
            .map_err(|_| EngineError::Property("CoolProp mutex poisoned".into()))?;
        st.value(q)
    }

    #[cfg(not(coolprop_linked))]
    fn value(&self, q: &Query) -> Result<f64, EngineError> {
        Err(EngineError::Property(format!(
            "CoolProp is not linked into this build ({})",
            q.describe()
        )))
    }
}

#[cfg(coolprop_linked)]
#[allow(unsafe_code)]
mod ffi {
    //! The only `unsafe` code of the AmCraX workspace: declarations and calls of CoolProp's C
    //! interface.
    use amcrax_engine::EngineError;
    use amcrax_engine::props::{Fluid, Imposed, Inputs, Output, Query};
    use std::collections::HashMap;
    use std::ffi::{CStr, CString, c_char, c_double, c_int, c_long};

    unsafe extern "C" {
        fn PropsSI(
            output: *const c_char,
            name1: *const c_char,
            prop1: c_double,
            name2: *const c_char,
            prop2: c_double,
            fluid: *const c_char,
        ) -> c_double;
        fn Props1SI(fluid: *const c_char, output: *const c_char) -> c_double;
        fn get_global_param_string(param: *const c_char, output: *mut c_char, n: c_int) -> c_long;
        fn get_param_index(param: *const c_char) -> c_long;
        fn get_input_pair_index(pair: *const c_char) -> c_long;
        fn AbstractState_factory(
            backend: *const c_char,
            fluids: *const c_char,
            errcode: *mut c_long,
            message_buffer: *mut c_char,
            buffer_length: c_long,
        ) -> c_long;
        fn AbstractState_specify_phase(
            handle: c_long,
            phase: *const c_char,
            errcode: *mut c_long,
            message_buffer: *mut c_char,
            buffer_length: c_long,
        );
        fn AbstractState_update(
            handle: c_long,
            input_pair: c_long,
            value1: c_double,
            value2: c_double,
            errcode: *mut c_long,
            message_buffer: *mut c_char,
            buffer_length: c_long,
        );
        fn AbstractState_keyed_output(
            handle: c_long,
            param: c_long,
            errcode: *mut c_long,
            message_buffer: *mut c_char,
            buffer_length: c_long,
        ) -> c_double;
    }

    const BUF: usize = 1024;

    fn cstr(s: &str) -> CString {
        // the arguments are fixed ASCII names without NUL bytes
        CString::new(s).unwrap_or_default()
    }

    fn buf_text(buf: &[c_char]) -> String {
        // SAFETY: CoolProp writes a NUL-terminated string into the buffer (zero-initialised, and
        // the last byte is never written because the length passed is BUF - 1).
        unsafe { CStr::from_ptr(buf.as_ptr()) }
            .to_string_lossy()
            .into_owned()
    }

    /// `get_global_param_string(param)`.
    pub fn global_string(param: &str) -> String {
        let p = cstr(param);
        let mut buf = [0 as c_char; BUF];
        // SAFETY: valid NUL-terminated input, writable buffer of the stated length (BUF - 1).
        let ok =
            unsafe { get_global_param_string(p.as_ptr(), buf.as_mut_ptr(), (BUF - 1) as c_int) };
        if ok == 1 {
            buf_text(&buf)
        } else {
            String::new()
        }
    }

    fn param_index(name: &str) -> Result<c_long, EngineError> {
        let p = cstr(name);
        // SAFETY: valid NUL-terminated input.
        let i = unsafe { get_param_index(p.as_ptr()) };
        if i < 0 {
            Err(EngineError::Property(format!(
                "CoolProp has no parameter {name}"
            )))
        } else {
            Ok(i)
        }
    }

    /// Reused imposed-phase states and the parameter indices.
    pub struct State {
        handles: HashMap<(Fluid, Imposed), c_long>,
        pt_inputs: c_long,
        params: HashMap<Output, c_long>,
    }

    impl State {
        pub fn new() -> Result<State, EngineError> {
            let pair = cstr("PT_INPUTS");
            // SAFETY: valid NUL-terminated input.
            let pt_inputs = unsafe { get_input_pair_index(pair.as_ptr()) };
            if pt_inputs < 0 {
                return Err(EngineError::Property("CoolProp has no PT_INPUTS".into()));
            }
            let mut params = HashMap::new();
            for o in [Output::Hmolar, Output::HmolarResidual, Output::Dmolar] {
                params.insert(o, param_index(o.name())?);
            }
            Ok(State {
                handles: HashMap::new(),
                pt_inputs,
                params,
            })
        }

        fn handle(&mut self, fluid: Fluid, phase: Imposed) -> Result<c_long, EngineError> {
            if let Some(h) = self.handles.get(&(fluid, phase)) {
                return Ok(*h);
            }
            let (be, fl) = (cstr("HEOS"), cstr(fluid.name()));
            let mut err: c_long = 0;
            let mut buf = [0 as c_char; BUF];
            // SAFETY: valid NUL-terminated inputs, error code and buffer of the stated length.
            let h = unsafe {
                AbstractState_factory(
                    be.as_ptr(),
                    fl.as_ptr(),
                    &mut err,
                    buf.as_mut_ptr(),
                    (BUF - 1) as c_long,
                )
            };
            if err != 0 {
                return Err(EngineError::Property(format!(
                    "AbstractState_factory: {}",
                    buf_text(&buf)
                )));
            }
            let ph = match phase {
                Imposed::Liquid => Some("phase_liquid"),
                Imposed::Gas => Some("phase_gas"),
                Imposed::None => None,
            };
            if let Some(ph) = ph {
                let p = cstr(ph);
                // SAFETY: handle from AbstractState_factory, valid string, error code and buffer.
                unsafe {
                    AbstractState_specify_phase(
                        h,
                        p.as_ptr(),
                        &mut err,
                        buf.as_mut_ptr(),
                        (BUF - 1) as c_long,
                    )
                };
                if err != 0 {
                    return Err(EngineError::Property(format!(
                        "specify_phase: {}",
                        buf_text(&buf)
                    )));
                }
            }
            self.handles.insert((fluid, phase), h);
            Ok(h)
        }

        fn props_si(
            out: &str,
            n1: &str,
            v1: f64,
            n2: &str,
            v2: f64,
            fluid: &str,
        ) -> Result<f64, EngineError> {
            let (o, a, b, f) = (cstr(out), cstr(n1), cstr(n2), cstr(fluid));
            // SAFETY: valid NUL-terminated inputs that outlive the call.
            let v = unsafe { PropsSI(o.as_ptr(), a.as_ptr(), v1, b.as_ptr(), v2, f.as_ptr()) };
            if v.is_finite() {
                Ok(v)
            } else {
                Err(EngineError::Property(format!(
                    "PropsSI({out}, {n1}, {v1:e}, {n2}, {v2:e}, {fluid}): {}",
                    global_string("errstring")
                )))
            }
        }

        pub fn value(&mut self, q: &Query) -> Result<f64, EngineError> {
            let fl = q.fluid.name();
            let out = q.out.name();
            match q.inputs {
                Inputs::Tp {
                    t_k,
                    p_pa,
                    phase: Imposed::None,
                } => Self::props_si(out, "T", t_k, "P", p_pa, fl),
                Inputs::Tp { t_k, p_pa, phase } => {
                    let h = self.handle(q.fluid, phase)?;
                    let param = *self.params.get(&q.out).ok_or_else(|| {
                        EngineError::Property(format!("output {out} not supported at (T, P)"))
                    })?;
                    let mut err: c_long = 0;
                    let mut buf = [0 as c_char; BUF];
                    // SAFETY: handle from AbstractState_factory, error code and buffer of the stated length.
                    unsafe {
                        AbstractState_update(
                            h,
                            self.pt_inputs,
                            p_pa,
                            t_k,
                            &mut err,
                            buf.as_mut_ptr(),
                            (BUF - 1) as c_long,
                        )
                    };
                    if err != 0 {
                        return Err(EngineError::Property(format!(
                            "update(PT_INPUTS): {}",
                            buf_text(&buf)
                        )));
                    }
                    // SAFETY: as above.
                    let v = unsafe {
                        AbstractState_keyed_output(
                            h,
                            param,
                            &mut err,
                            buf.as_mut_ptr(),
                            (BUF - 1) as c_long,
                        )
                    };
                    if err != 0 {
                        return Err(EngineError::Property(format!(
                            "keyed_output({out}): {}",
                            buf_text(&buf)
                        )));
                    }
                    Ok(v)
                }
                Inputs::Tq { t_k, q: qv } => Self::props_si(out, "T", t_k, "Q", qv, fl),
                Inputs::Pq { p_pa, q: qv } => Self::props_si(out, "P", p_pa, "Q", qv, fl),
                Inputs::Constant => {
                    let (f, o) = (cstr(fl), cstr(out));
                    // SAFETY: valid NUL-terminated inputs.
                    let v = unsafe { Props1SI(f.as_ptr(), o.as_ptr()) };
                    if v.is_finite() {
                        Ok(v)
                    } else {
                        Err(EngineError::Property(format!(
                            "Props1SI({fl}, {out}): {}",
                            global_string("errstring")
                        )))
                    }
                }
            }
        }
    }
}
