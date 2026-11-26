/* HealthSphere frontend configuration */
const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);

window.HEALTHSPHERE_CONFIG = Object.freeze({
    API_BASE_URL: isLocal
        ? "http://127.0.0.1:8000"
        : "https://healthsphere-api-7l31.onrender.com"
});
