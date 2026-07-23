<script>
const configuredBackendHost = String(
  process.env.VUE_APP_BACKEND_IP || ""
).trim();
const currentHost = window.location.hostname;
const backendHost =
  configuredBackendHost &&
  !["localhost", "127.0.0.1"].includes(configuredBackendHost)
    ? configuredBackendHost
    : currentHost;
const backendPort = process.env.VUE_APP_BACKEND_PORT || "5008";
const BASEURL = `${window.location.protocol}//${backendHost}:${backendPort}/`;
export default {
  BASEURL,
};
</script>
