
function goSegmentation() {
    this.isNavigator = false;
    if (this.$route.path === "/segmentation") {
        this.$message.success('您已经在该界面了哦')
    } else this.$router.push("segmentation");
}

function goSpectralIndices() {
    this.isNavigator = false;
    if (this.$route.path === "/spectralindices") {
        this.$message.success('您已经在该界面了哦')
    } else this.$router.push("spectralindices");
}

export { goSegmentation, goSpectralIndices }
