/**
 * DSH host half. Voice admission stays on DSH's public browser Session face;
 * local audio and speech inference stay in the separately supervised Muxiva
 * process. Keeping this half empty avoids a second web server or agent loop.
 */
export const name = 'muxiva-dsh-voice'

export function apply() {}
