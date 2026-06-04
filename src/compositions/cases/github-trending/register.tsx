import { Composition } from "remotion";
import { DEFAULT_VIDEO_CONFIG } from "../../common/video";
import { GitHubTrending, githubTrendingSchema } from "./GitHubTrending";
import { trendingData } from "./data";

export const GitHubTrendingCompositions: React.FC = () => {
  return (
    <Composition
      id="GitHubTrending"
      component={GitHubTrending}
      durationInFrames={4346}
      schema={githubTrendingSchema}
      defaultProps={trendingData}
      {...DEFAULT_VIDEO_CONFIG}
    />
  );
};
