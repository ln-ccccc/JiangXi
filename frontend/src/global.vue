<script>
import { buildBackendUrl } from "./utils/backendUrl.mjs";

const BASEURL = buildBackendUrl(process.env.VUE_APP_BACKEND_URL, window.location);
export default {
  BASEURL,
};
</script>
