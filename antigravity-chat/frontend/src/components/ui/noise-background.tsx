import React from "react";
import { cn } from "@/lib/utils";

interface NoiseBackgroundProps {
    children?: React.ReactNode;
    className?: string;
    containerClassName?: string;
    gradientColors?: string[];
    noiseIntensity?: number;
    speed?: number;
    backdropBlur?: boolean;
    animating?: boolean;
}

export const NoiseBackground: React.FC<NoiseBackgroundProps> = ({
    children,
    className,
    containerClassName,
    gradientColors = ["rgb(255, 100, 150)", "rgb(100, 150, 255)", "rgb(255, 200, 100)"],
    noiseIntensity = 0.2,
    speed = 0.1,
    backdropBlur = false,
    animating = true,
}) => {
    return (
        <div
            className={cn(
                "relative flex h-full w-full items-center justify-center overflow-hidden bg-neutral-100 dark:bg-neutral-900",
                containerClassName
            )}
        >
            <div className="absolute inset-0 z-0">
                <div
                    className={cn(
                        "absolute inset-0 opacity-50 blur-3xl",
                        animating && "animate-pulse"
                    )}
                    style={{
                        background: `radial-gradient(circle at center, ${gradientColors.join(
                            ", "
                        )})`,
                        transition: `all ${5 / speed}s ease-in-out`,
                    }}
                />
                {/* Noise Layer */}
                <div
                    className="absolute inset-0 opacity-[0.15] mix-blend-overlay"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                    }}
                />
            </div>
            <div className={cn("relative z-10 w-full", className)}>{children}</div>
        </div>
    );
};
