import { Composition } from "remotion";
import { DEFAULT_VIDEO_CONFIG } from "../../common/video";
import { HelloWorld, helloWorldSchema } from "./HelloWorld";
import { Logo, logoSchema } from "./Logo";

export const HelloWorldCompositions: React.FC = () => {
  return (
    <>
      <Composition
        id="HelloWorld"
        component={HelloWorld}
        durationInFrames={150}
        schema={helloWorldSchema}
        defaultProps={{
          titleText: "Welcome to Remotion",
          titleColor: "#FFFFFF",
          subtitleText: "每一帧都是一个 React 组件",
          accentColor: "#86A8E7",
        }}
        {...DEFAULT_VIDEO_CONFIG}
      />

      <Composition
        id="OnlyLogo"
        component={Logo}
        durationInFrames={150}
        schema={logoSchema}
        defaultProps={{
          logoColor1: "#91dAE2",
          logoColor2: "#86A8E7",
        }}
        {...DEFAULT_VIDEO_CONFIG}
      />
    </>
  );
};
